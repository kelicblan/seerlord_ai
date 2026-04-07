import { ref, onMounted, onUnmounted } from 'vue';
import { OfflineStorage, SyncQueue, type SyncQueueItem } from '@/utils/storage';

export interface UseOfflineStorageReturn<T = unknown> {
  isReady: ReturnType<typeof ref<boolean>>;
  isOnline: ReturnType<typeof ref<boolean>>;
  pendingSyncCount: ReturnType<typeof ref<number>>;
  storage: OfflineStorage;
  syncQueue: SyncQueue;
  set: <U extends T>(key: string, value: U, ttl?: number) => Promise<void>;
  get: <U extends T>(key: string) => Promise<U | null>;
  remove: (key: string) => Promise<void>;
  clear: () => Promise<void>;
  has: (key: string) => Promise<boolean>;
  keys: () => Promise<string[]>;
  enqueueSync: (
    item: Omit<SyncQueueItem<T>, 'id' | 'timestamp' | 'retries'>
  ) => Promise<void>;
  processSync: (
    processor: (item: SyncQueueItem<T>) => Promise<boolean>
  ) => Promise<{ success: number; failed: number }>;
  clearSyncQueue: () => Promise<void>;
}

export interface OfflineStorageConfig {
  databaseName?: string;
  version?: number;
  storeName?: string;
}

const DEFAULT_DB_CONFIG = {
  databaseName: 'vue-offline-storage',
  version: 1,
  storeName: 'offline-data',
};

export const useOfflineStorage = <T = unknown>(
  config: OfflineStorageConfig = {}
): UseOfflineStorageReturn<T> => {
  const dbConfig = { ...DEFAULT_DB_CONFIG, ...config };

  const isReady = ref(false);
  const isOnline = ref(navigator.onLine);
  const pendingSyncCount = ref(0);

  const storage = new OfflineStorage({
    databaseName: dbConfig.databaseName!,
    version: dbConfig.version!,
    storeName: dbConfig.storeName!,
  });

  const syncQueue = new SyncQueue(storage);

  const initStorage = async () => {
    try {
      await storage.init();
      await syncQueue.loadQueue();
      pendingSyncCount.value = syncQueue.size;
      isReady.value = true;
    } catch (error) {
      console.error('离线存储初始化失败:', error);
      isReady.value = false;
    }
  };

  const handleOnline = () => {
    isOnline.value = true;
  };

  const handleOffline = () => {
    isOnline.value = false;
  };

  const set = async <U extends T>(
    key: string,
    value: U,
    ttl?: number
  ): Promise<void> => {
    await storage.set(key, value, ttl);
  };

  const get = async <U extends T>(key: string): Promise<U | null> => {
    return await storage.get<U>(key);
  };

  const remove = async (key: string): Promise<void> => {
    await storage.delete(key);
  };

  const clear = async (): Promise<void> => {
    await storage.clear();
  };

  const has = async (key: string): Promise<boolean> => {
    return await storage.has(key);
  };

  const keys = async (): Promise<string[]> => {
    return await storage.keys();
  };

  const enqueueSync = async (
    item: Omit<SyncQueueItem<T>, 'id' | 'timestamp' | 'retries'>
  ): Promise<void> => {
    await syncQueue.enqueue(item);
    pendingSyncCount.value = syncQueue.size;
  };

  const processSync = async (
    processor: (item: SyncQueueItem<T>) => Promise<boolean>
  ): Promise<{ success: number; failed: number }> => {
    const result = await syncQueue.processQueue(processor);
    pendingSyncCount.value = syncQueue.size;
    return result;
  };

  const clearSyncQueue = async (): Promise<void> => {
    await syncQueue.clear();
    pendingSyncCount.value = 0;
  };

  onMounted(async () => {
    await initStorage();

    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);
  });

  onUnmounted(() => {
    window.removeEventListener('online', handleOnline);
    window.removeEventListener('offline', handleOffline);
  });

  return {
    isReady,
    isOnline,
    pendingSyncCount,
    storage,
    syncQueue,
    set,
    get,
    remove,
    clear,
    has,
    keys,
    enqueueSync,
    processSync,
    clearSyncQueue,
  };
};
