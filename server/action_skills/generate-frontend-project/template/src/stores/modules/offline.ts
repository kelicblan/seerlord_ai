import { ref, computed } from 'vue';
import { defineStore } from 'pinia';
import type { OfflineDataItem } from '../types';

const MAX_RETRY_COUNT = 3;
const OFFLINE_STORAGE_KEY = 'offline-pending-data';

export const useOfflineStore = defineStore(
  'offline',
  () => {
    const isOnline = ref(navigator.onLine);
    const pendingData = ref<OfflineDataItem[]>([]);
    const lastSyncTime = ref<number | null>(null);
    const syncStatus = ref<'idle' | 'syncing' | 'success' | 'failed'>('idle');
    const syncError = ref<string | null>(null);

    const pendingCount = computed(() => pendingData.value.length);
    const hasPendingData = computed(() => pendingData.value.length > 0);

    const initializeOnlineStatus = () => {
      window.addEventListener('online', () => {
        isOnline.value = true;
        console.log('Network connection restored');
      });

      window.addEventListener('offline', () => {
        isOnline.value = false;
        console.log('Network connection lost');
      });
    };

    const loadPendingData = () => {
      try {
        const stored = localStorage.getItem(OFFLINE_STORAGE_KEY);
        if (stored) {
          pendingData.value = JSON.parse(stored);
        }
      } catch (error) {
        console.error('Failed to load pending offline data:', error);
        pendingData.value = [];
      }
    };

    const savePendingData = () => {
      try {
        localStorage.setItem(OFFLINE_STORAGE_KEY, JSON.stringify(pendingData.value));
      } catch (error) {
        console.error('Failed to save pending offline data:', error);
      }
    };

    const setOnlineStatus = (online: boolean) => {
      isOnline.value = online;
    };

    const setOfflineData = (
      type: string,
      data: unknown,
      metadata?: Record<string, unknown>,
    ) => {
      const item: OfflineDataItem = {
        id: `${type}-${Date.now()}-${Math.random().toString(36).substring(7)}`,
        type,
        data,
        timestamp: Date.now(),
        retryCount: 0,
        metadata,
      };

      pendingData.value.push(item);
      savePendingData();

      console.log(`Offline data added: ${type}`, item);
    };

    const getOfflineData = (type?: string): OfflineDataItem[] | OfflineDataItem | null => {
      if (type) {
        const items = pendingData.value.filter(item => item.type === type);
        return items.length > 0 ? items : null;
      }

      return pendingData.value;
    };

    const clearOfflineData = (type?: string) => {
      if (type) {
        pendingData.value = pendingData.value.filter(item => item.type !== type);
      } else {
        pendingData.value = [];
      }

      savePendingData();
      console.log(`Offline data cleared: ${type || 'all'}`);
    };

    const removePendingItem = (id: string) => {
      const index = pendingData.value.findIndex(item => item.id === id);
      if (index !== -1) {
        pendingData.value.splice(index, 1);
        savePendingData();
      }
    };

    const updatePendingItem = (id: string, updates: Partial<OfflineDataItem>) => {
      const index = pendingData.value.findIndex(item => item.id === id);
      if (index !== -1) {
        pendingData.value[index] = {
          ...pendingData.value[index],
          ...updates,
        };
        savePendingData();
      }
    };

    const syncSingleItem = async (item: OfflineDataItem): Promise<boolean> => {
      try {
        const response = await fetch(`/api/offline/sync`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            type: item.type,
            data: item.data,
            timestamp: item.timestamp,
            metadata: item.metadata,
          }),
        });

        if (response.ok) {
          removePendingItem(item.id);
          return true;
        }

        if (response.status >= 500) {
          throw new Error('Server error');
        }

        return false;
      } catch (error) {
        console.error(`Failed to sync item ${item.id}:`, error);
        return false;
      }
    };

    const syncOfflineData = async () => {
      if (!isOnline.value) {
        console.log('Cannot sync: offline');
        return;
      }

      if (pendingData.value.length === 0) {
        console.log('No pending data to sync');
        return;
      }

      updateSyncStatus('syncing');

      const itemsToSync = [...pendingData.value];
      let successCount = 0;
      let failCount = 0;

      for (const item of itemsToSync) {
        if (item.retryCount >= MAX_RETRY_COUNT) {
          console.warn(`Skipping item ${item.id}: max retries exceeded`);
          continue;
        }

        const success = await syncSingleItem(item);

        if (success) {
          successCount++;
        } else {
          failCount++;
          updatePendingItem(item.id, {
            retryCount: item.retryCount + 1,
          });
        }
      }

      lastSyncTime.value = Date.now();

      if (failCount === 0) {
        updateSyncStatus('success');
      } else if (successCount > 0) {
        updateSyncStatus('failed', `Partially synced: ${successCount} succeeded, ${failCount} failed`);
      } else {
        updateSyncStatus('failed', 'All items failed to sync');
      }

      console.log(`Sync completed: ${successCount} succeeded, ${failCount} failed`);
    };

    const updateSyncStatus = (status: 'idle' | 'syncing' | 'success' | 'failed', error?: string) => {
      syncStatus.value = status;
      syncError.value = error || null;
    };

    const getPendingDataByType = (type: string): OfflineDataItem[] => {
      return pendingData.value.filter(item => item.type === type);
    };

    const getTotalPendingCount = (): number => {
      return pendingData.value.length;
    };

    const getRetryableItems = (): OfflineDataItem[] => {
      return pendingData.value.filter(item => item.retryCount < MAX_RETRY_COUNT);
    };

    const autoSyncIfOnline = () => {
      if (isOnline.value && hasPendingData.value) {
        console.log('Auto-syncing pending data...');
        syncOfflineData();
      }
    };

    initializeOnlineStatus();
    loadPendingData();

    if (typeof window !== 'undefined') {
      window.addEventListener('online', () => {
        setTimeout(autoSyncIfOnline, 1000);
      });
    }

    return {
      isOnline,
      pendingData,
      lastSyncTime,
      syncStatus,
      syncError,
      pendingCount,
      hasPendingData,
      setOnlineStatus,
      setOfflineData,
      getOfflineData,
      clearOfflineData,
      syncOfflineData,
      updateSyncStatus,
      getPendingDataByType,
      getTotalPendingCount,
      getRetryableItems,
      removePendingItem,
      updatePendingItem,
    };
  },
  {
    persist: {
      key: 'offline-state',
      pick: ['lastSyncTime'],
    },
  },
);
