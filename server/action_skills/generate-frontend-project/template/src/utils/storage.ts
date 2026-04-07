export interface StorageItem<T = unknown> {
  key: string;
  value: T;
  timestamp: number;
  expiresAt?: number;
}

export interface IndexedDBConfig {
  databaseName: string;
  version: number;
  storeName: string;
}

export class OfflineStorage {
  private db: IDBDatabase | null = null;
  private config: IndexedDBConfig;

  constructor(config: IndexedDBConfig) {
    this.config = config;
  }

  async init(): Promise<void> {
    return new Promise((resolve, reject) => {
      const request = indexedDB.open(this.config.databaseName, this.config.version);

      request.onerror = () => {
        reject(new Error('Failed to open IndexedDB'));
      };

      request.onsuccess = () => {
        this.db = request.result;
        resolve();
      };

      request.onupgradeneeded = (event) => {
        const db = (event.target as IDBOpenDBRequest).result;

        if (!db.objectStoreNames.contains(this.config.storeName)) {
          db.createObjectStore(this.config.storeName, { keyPath: 'key' });
        }
      };
    });
  }

  async set<T>(key: string, value: T, ttl?: number): Promise<void> {
    if (!this.db) {
      await this.init();
    }

    return new Promise((resolve, reject) => {
      const transaction = this.db!.transaction([this.config.storeName], 'readwrite');
      const store = transaction.objectStore(this.config.storeName);

      const item: StorageItem<T> = {
        key,
        value,
        timestamp: Date.now(),
        expiresAt: ttl ? Date.now() + ttl : undefined,
      };

      const request = store.put(item);

      request.onsuccess = () => resolve();
      request.onerror = () => reject(new Error(`Failed to set item: ${key}`));
    });
  }

  async get<T>(key: string): Promise<T | null> {
    if (!this.db) {
      await this.init();
    }

    return new Promise((resolve, reject) => {
      const transaction = this.db!.transaction([this.config.storeName], 'readonly');
      const store = transaction.objectStore(this.config.storeName);
      const request = store.get(key);

      request.onsuccess = () => {
        const item = request.result as StorageItem<T> | undefined;

        if (!item) {
          resolve(null);
          return;
        }

        if (item.expiresAt && Date.now() > item.expiresAt) {
          this.delete(key).catch(console.error);
          resolve(null);
          return;
        }

        resolve(item.value);
      };

      request.onerror = () => reject(new Error(`Failed to get item: ${key}`));
    });
  }

  async delete(key: string): Promise<void> {
    if (!this.db) {
      await this.init();
    }

    return new Promise((resolve, reject) => {
      const transaction = this.db!.transaction([this.config.storeName], 'readwrite');
      const store = transaction.objectStore(this.config.storeName);
      const request = store.delete(key);

      request.onsuccess = () => resolve();
      request.onerror = () => reject(new Error(`Failed to delete item: ${key}`));
    });
  }

  async clear(): Promise<void> {
    if (!this.db) {
      await this.init();
    }

    return new Promise((resolve, reject) => {
      const transaction = this.db!.transaction([this.config.storeName], 'readwrite');
      const store = transaction.objectStore(this.config.storeName);
      const request = store.clear();

      request.onsuccess = () => resolve();
      request.onerror = () => reject(new Error('Failed to clear store'));
    });
  }

  async keys(): Promise<string[]> {
    if (!this.db) {
      await this.init();
    }

    return new Promise((resolve, reject) => {
      const transaction = this.db!.transaction([this.config.storeName], 'readonly');
      const store = transaction.objectStore(this.config.storeName);
      const request = store.getAllKeys();

      request.onsuccess = () => {
        resolve(request.result as string[]);
      };

      request.onerror = () => reject(new Error('Failed to get keys'));
    });
  }

  async has(key: string): Promise<boolean> {
    const value = await this.get(key);
    return value !== null;
  }
}

export interface SyncQueueItem<T = unknown> {
  id: string;
  type: 'create' | 'update' | 'delete';
  endpoint: string;
  data?: T;
  timestamp: number;
  retries: number;
  maxRetries: number;
}

export class SyncQueue {
  private storage: OfflineStorage;
  private queue: SyncQueueItem[] = [];
  private isProcessing = false;

  constructor(storage: OfflineStorage) {
    this.storage = storage;
  }

  async enqueue<T>(item: Omit<SyncQueueItem<T>, 'id' | 'timestamp' | 'retries'>): Promise<void> {
    const queueItem: SyncQueueItem<T> = {
      ...item,
      id: `${Date.now()}-${Math.random().toString(36).substring(2, 9)}`,
      timestamp: Date.now(),
      retries: 0,
      maxRetries: item.maxRetries || 3,
    } as SyncQueueItem<T>;

    this.queue.push(queueItem);
    await this.persistQueue();
  }

  async dequeue(): Promise<SyncQueueItem | undefined> {
    const item = this.queue.shift();
    await this.persistQueue();
    return item;
  }

  async peek(): Promise<SyncQueueItem | undefined> {
    return this.queue[0];
  }

  get size(): number {
    return this.queue.length;
  }

  isEmpty(): boolean {
    return this.queue.length === 0;
  }

  async updateRetry(itemId: string): Promise<void> {
    const item = this.queue.find((i) => i.id === itemId);
    if (item) {
      item.retries++;
      await this.persistQueue();
    }
  }

  async removeItem(itemId: string): Promise<void> {
    this.queue = this.queue.filter((i) => i.id !== itemId);
    await this.persistQueue();
  }

  async clear(): Promise<void> {
    this.queue = [];
    await this.persistQueue();
  }

  private async persistQueue(): Promise<void> {
    await this.storage.set('sync_queue', this.queue);
  }

  async loadQueue(): Promise<void> {
    const stored = await this.storage.get<SyncQueueItem[]>('sync_queue');
    if (stored) {
      this.queue = stored;
    }
  }

  async processQueue<T>(
    processor: (item: SyncQueueItem<T>) => Promise<boolean>
  ): Promise<{ success: number; failed: number }> {
    if (this.isProcessing) {
      throw new Error('Queue is already being processed');
    }

    this.isProcessing = true;
    let success = 0;
    let failed = 0;

    try {
      await this.loadQueue();

      while (!this.isEmpty()) {
        const item = await this.peek();
        if (!item) break;

        try {
          const result = await processor(item as SyncQueueItem<T>);

          if (result) {
            await this.dequeue();
            success++;
          } else {
            await this.updateRetry(item.id);

            if (item.retries >= item.maxRetries) {
              await this.removeItem(item.id);
              failed++;
            } else {
              break;
            }
          }
        } catch (error) {
          console.error('Failed to process queue item:', error);
          await this.updateRetry(item.id);

          if (item.retries >= item.maxRetries) {
            await this.removeItem(item.id);
            failed++;
          }
          break;
        }
      }
    } finally {
      this.isProcessing = false;
    }

    return { success, failed };
  }
}
