const UTF8Encoder = new TextEncoder();
const UTF8Decoder = new TextDecoder();

export const md5 = async (message: string): Promise<string> => {
  const msgBuffer = UTF8Encoder.encode(message);
  const hashBuffer = await crypto.subtle.digest('SHA-256', msgBuffer);
  return arrayBufferToHex(hashBuffer).substring(0, 32);
};

export const sha256 = async (message: string): Promise<string> => {
  const msgBuffer = UTF8Encoder.encode(message);
  const hashBuffer = await crypto.subtle.digest('SHA-256', msgBuffer);
  return arrayBufferToHex(hashBuffer);
};

export const sha512 = async (message: string): Promise<string> => {
  const msgBuffer = UTF8Encoder.encode(message);
  const hashBuffer = await crypto.subtle.digest('SHA-512', msgBuffer);
  return arrayBufferToHex(hashBuffer);
};

const arrayBufferToHex = (buffer: ArrayBuffer): string => {
  const byteArray = new Uint8Array(buffer);
  return Array.from(byteArray)
    .map((byte) => byte.toString(16).padStart(2, '0'))
    .join('');
};

export const base64Encode = (str: string): string => {
  const bytes = UTF8Encoder.encode(str);
  let binary = '';
  for (let i = 0; i < bytes.length; i++) {
    binary += String.fromCharCode(bytes[i]);
  }
  return btoa(binary);
};

export const base64Decode = (encoded: string): string => {
  const binary = atob(encoded);
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i++) {
    bytes[i] = binary.charCodeAt(i);
  }
  return UTF8Decoder.decode(bytes);
};

export interface AesKeyConfig {
  name: string;
  length: number;
}

const DEFAULT_AES_CONFIG: AesKeyConfig = {
  name: 'AES-GCM',
  length: 256,
};

const deriveKey = async (password: string, salt: Uint8Array): Promise<CryptoKey> => {
  const keyMaterial = await crypto.subtle.importKey(
    'raw',
    UTF8Encoder.encode(password),
    'PBKDF2',
    false,
    ['deriveKey']
  );

  return crypto.subtle.deriveKey(
    {
      name: 'PBKDF2',
      salt,
      iterations: 100000,
      hash: 'SHA-256',
    },
    keyMaterial,
    { name: DEFAULT_AES_CONFIG.name, length: DEFAULT_AES_CONFIG.length },
    false,
    ['encrypt', 'decrypt']
  );
};

const generateSalt = (): Uint8Array => {
  return crypto.getRandomValues(new Uint8Array(16));
};

const arrayBufferToBase64 = (buffer: ArrayBuffer): string => {
  const bytes = new Uint8Array(buffer);
  let binary = '';
  for (let i = 0; i < bytes.length; i++) {
    binary += String.fromCharCode(bytes[i]);
  }
  return btoa(binary);
};

const base64ToArrayBuffer = (base64: string): Uint8Array => {
  const binary = atob(base64);
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i++) {
    bytes[i] = binary.charCodeAt(i);
  }
  return bytes;
};

export interface AesEncryptResult {
  ciphertext: string;
  iv: string;
  salt: string;
}

export const aesEncrypt = async (
  plaintext: string,
  password: string,
  config?: AesKeyConfig
): Promise<AesEncryptResult> => {
  const salt = generateSalt();
  const iv = crypto.getRandomValues(new Uint8Array(12));
  const key = await deriveKey(password, salt);

  const encoded = UTF8Encoder.encode(plaintext);
  const ciphertext = await crypto.subtle.encrypt(
    { name: config?.name ?? DEFAULT_AES_CONFIG.name, iv },
    key,
    encoded
  );

  return {
    ciphertext: arrayBufferToBase64(ciphertext),
    iv: arrayBufferToBase64(iv),
    salt: arrayBufferToBase64(salt),
  };
};

export const aesDecrypt = async (
  encrypted: AesEncryptResult,
  password: string,
  config?: AesKeyConfig
): Promise<string> => {
  const salt = base64ToArrayBuffer(encrypted.salt);
  const iv = base64ToArrayBuffer(encrypted.iv);
  const ciphertext = base64ToArrayBuffer(encrypted.ciphertext);

  const key = await deriveKey(password, salt);

  const decrypted = await crypto.subtle.decrypt(
    { name: config?.name ?? DEFAULT_AES_CONFIG.name, iv },
    key,
    ciphertext
  );

  return UTF8Decoder.decode(decrypted);
};
