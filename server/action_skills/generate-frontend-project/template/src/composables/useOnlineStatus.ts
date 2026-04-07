import { ref, onMounted, onUnmounted, readonly } from 'vue';

export interface UseOnlineStatusReturn {
  isOnline: ReturnType<typeof ref<boolean>>;
  wasOffline: ReturnType<typeof ref<boolean>>;
  isReconnecting: ReturnType<typeof ref<boolean>>;
  lastOnlineTime: ReturnType<typeof ref<number | null>>;
  lastOfflineTime: ReturnType<typeof ref<number | null>>;
  checkConnection: () => Promise<boolean>;
  addOnlineListener: (callback: () => void) => () => void;
  addOfflineListener: (callback: () => void) => () => void;
}

const onlineCallbacks: Array<() => void> = [];
const offlineCallbacks: Array<() => void> = [];

export const useOnlineStatus = (): UseOnlineStatusReturn => {
  const isOnline = ref(navigator.onLine);
  const wasOffline = ref(false);
  const isReconnecting = ref(false);
  const lastOnlineTime = ref<number | null>(
    navigator.onLine ? Date.now() : null
  );
  const lastOfflineTime = ref<number | null>(
    navigator.onLine ? null : Date.now()
  );

  let reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  const RECONNECT_INTERVAL = 5000;
  const MAX_RECONNECT_ATTEMPTS = 3;
  let reconnectAttempts = 0;

  const handleOnline = () => {
    isOnline.value = true;
    lastOnlineTime.value = Date.now();

    if (wasOffline.value) {
      isReconnecting.value = true;
      setTimeout(() => {
        isReconnecting.value = false;
        wasOffline.value = false;
      }, 1000);
    }

    reconnectAttempts = 0;
    onlineCallbacks.forEach((callback) => callback());
  };

  const handleOffline = () => {
    isOnline.value = false;
    lastOfflineTime.value = Date.now();
    wasOffline.value = true;
    offlineCallbacks.forEach((callback) => callback());

    attemptReconnect();
  };

  const attemptReconnect = () => {
    if (reconnectAttempts >= MAX_RECONNECT_ATTEMPTS) {
      console.warn('最大重连尝试次数已达成');
      return;
    }

    if (reconnectTimer) {
      clearTimeout(reconnectTimer);
    }

    reconnectTimer = setTimeout(async () => {
      reconnectAttempts++;
      const isConnected = await checkConnection();

      if (isConnected) {
        handleOnline();
      } else {
        attemptReconnect();
      }
    }, RECONNECT_INTERVAL);
  };

  const checkConnection = async (): Promise<boolean> => {
    try {
      const response = await fetch('/api/health', {
        method: 'HEAD',
        cache: 'no-cache',
      });
      return response.ok;
    } catch {
      return false;
    }
  };

  const addOnlineListener = (callback: () => void): (() => void) => {
    onlineCallbacks.push(callback);
    return () => {
      const index = onlineCallbacks.indexOf(callback);
      if (index > -1) {
        onlineCallbacks.splice(index, 1);
      }
    };
  };

  const addOfflineListener = (callback: () => void): (() => void) => {
    offlineCallbacks.push(callback);
    return () => {
      const index = offlineCallbacks.indexOf(callback);
      if (index > -1) {
        offlineCallbacks.splice(index, 1);
      }
    };
  };

  onMounted(() => {
    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);
  });

  onUnmounted(() => {
    window.removeEventListener('online', handleOnline);
    window.removeEventListener('offline', handleOffline);

    if (reconnectTimer) {
      clearTimeout(reconnectTimer);
    }
  });

  return {
    isOnline: readonly(isOnline),
    wasOffline: readonly(wasOffline),
    isReconnecting: readonly(isReconnecting),
    lastOnlineTime: readonly(lastOnlineTime),
    lastOfflineTime: readonly(lastOfflineTime),
    checkConnection,
    addOnlineListener,
    addOfflineListener,
  };
};
