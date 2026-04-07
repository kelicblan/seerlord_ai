export const downloadFile = (blob: Blob | string, filename: string, mimeType?: string): void => {
  let blobData: Blob;

  if (typeof blob === 'string') {
    const content = mimeType ? [blob] : [blob];
    blobData = new Blob(content, { type: mimeType ?? 'text/plain' });
  } else {
    blobData = blob;
  }

  const url = URL.createObjectURL(blobData);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  link.style.display = 'none';

  document.body.appendChild(link);
  link.click();

  document.body.removeChild(link);
  URL.revokeObjectURL(url);
};

export const getFileExtension = (filename: string): string => {
  if (!filename) return '';
  const parts = filename.split('.');
  return parts.length > 1 ? parts[parts.length - 1].toLowerCase() : '';
};

export const isImageFile = (file: File | { name?: string; type?: string } | string): boolean => {
  if (!file) return false;

  const imageMimeTypes = [
    'image/jpeg',
    'image/png',
    'image/gif',
    'image/bmp',
    'image/webp',
    'image/svg+xml',
    'image/tiff',
  ];

  if (file instanceof File) {
    return imageMimeTypes.includes(file.type);
  }

  if (typeof file === 'string') {
    const ext = getFileExtension(file);
    const imageExtensions = ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp', 'svg', 'tiff', 'tif'];
    return imageExtensions.includes(ext);
  }

  if (file.type) {
    return imageMimeTypes.includes(file.type);
  }

  if (file.name) {
    const ext = getFileExtension(file.name);
    const imageExtensions = ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp', 'svg', 'tiff', 'tif'];
    return imageExtensions.includes(ext);
  }

  return false;
};

export const formatFileSize = (bytes: number | string): string => {
  const size = typeof bytes === 'string' ? parseInt(bytes, 10) : bytes;
  if (isNaN(size) || size < 0) {
    return '0 B';
  }

  const units = ['B', 'KB', 'MB', 'GB', 'TB', 'PB'];
  let unitIndex = 0;
  let fileSize = size;

  while (fileSize >= 1024 && unitIndex < units.length - 1) {
    fileSize /= 1024;
    unitIndex++;
  }

  return `${fileSize.toFixed(2)} ${units[unitIndex]}`;
};

export const getFileMimeType = (file: File | string): string => {
  if (file instanceof File) {
    return file.type;
  }

  const extension = getFileExtension(file);
  const mimeTypes: Record<string, string> = {
    jpg: 'image/jpeg',
    jpeg: 'image/jpeg',
    png: 'image/png',
    gif: 'image/gif',
    bmp: 'image/bmp',
    webp: 'image/webp',
    svg: 'image/svg+xml',
    tiff: 'image/tiff',
    tif: 'image/tiff',
    pdf: 'application/pdf',
    doc: 'application/msword',
    docx: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    xls: 'application/vnd.ms-excel',
    xlsx: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    ppt: 'application/vnd.ms-powerpoint',
    pptx: 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
    zip: 'application/zip',
    rar: 'application/x-rar-compressed',
    '7z': 'application/x-7z-compressed',
    txt: 'text/plain',
    html: 'text/html',
    css: 'text/css',
    js: 'text/javascript',
    json: 'application/json',
    xml: 'application/xml',
    mp3: 'audio/mpeg',
    wav: 'audio/wav',
    mp4: 'video/mp4',
    avi: 'video/x-msvideo',
    mov: 'video/quicktime',
  };

  return mimeTypes[extension] ?? 'application/octet-stream';
};

export const readFileAsDataURL = (file: File): Promise<string> => {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result as string);
    reader.onerror = () => reject(new Error('Failed to read file'));
    reader.readAsDataURL(file);
  });
};

export const readFileAsText = (file: File): Promise<string> => {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result as string);
    reader.onerror = () => reject(new Error('Failed to read file'));
    reader.readAsText(file);
  });
};
