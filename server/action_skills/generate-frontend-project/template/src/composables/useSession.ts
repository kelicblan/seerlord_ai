import { ref, onMounted, onUnmounted, readonly } from 'vue';

export interface SessionConfig {
  timeout?: number;
  warningBefore?: number;
  refreshEnabled?: boolean;
  refreshInterval?: number;
}

export interface UseSessionReturn {
  isExpired: ReturnType<typeof ref<boolean>>;
  isWarning: ReturnType<typeof ref<boolean>>;
  remainingTime: ReturnType<typeof ref<number>>;
  lastActivity: ReturnType<typeof ref<number>>;
  resetTimer: () => void;
  extendSession: () => void;
  destroySession: () => void;
  onWarning: (callback: (remaining: number) => void) => () => void;
  onExpired: (callback: () => void) => void;
}

const SESSION_TIMEOUT_KEY = 'vue-session-timeout';
const SESSION_ACTIVITY_KEY = 'vue-session-activity';

const defaultConfig: Required<SessionConfig> = {
  timeout: 30 * 60 * 1000,
  warningBefore: 5 * 60 * 1000,
  refreshEnabled: true,
  refreshInterval: 10 * 60 * 1000,
};

const warningCallbacks: Array<(remaining: number) => void> = [];
const expiredCallbacks: Array<() => void> = [];

export const useSession = (config: SessionConfig = {}): UseSessionReturn => {
  const mergedConfig = { ...defaultConfig, ...config };

  const isExpired = ref(false);
  const isWarning = ref(false);
  const remainingTime = ref(mergedConfig.timeout);
  const lastActivity = ref(Date.now());

  let activityTimer: ReturnType<typeof setInterval> | null = null;
  let warningTimer: ReturnType<typeof setInterval> | null = null;
  let refreshTimer: ReturnType<typeof setInterval> | null = null;

  const updateActivity = () => {
    lastActivity.value = Date.now();
    localStorage.setItem(SESSION_ACTIVITY_KEY, lastActivity.value.toString());
    isExpired.value = false;
    isWarning.value = false;
  };

  const checkSession = () => {
    if (isExpired.value) return;

    const now = Date.now();
    const elapsed = now - lastActivity.value;
    remainingTime.value = Math.max(0, mergedConfig.timeout - elapsed);

    if (remainingTime.value <= 0) {
      handleExpired();
      return;
    }

    if (remainingTime.value <= mergedConfig.warningBefore && !isWarning.value) {
      isWarning.value = true;
      warningCallbacks.forEach((callback) => callback(remainingTime.value));
    }
  };

  const handleExpired = () => {
    isExpired.value = true;
    isWarning.value = false;
    clearTimers();
    expiredCallbacks.forEach((callback) => callback());
  };

  const resetTimer = () => {
    updateActivity();
  };

  const extendSession = () => {
    resetTimer();
  };

  const destroySession = () => {
    handleExpired();
    localStorage.removeItem(SESSION_TIMEOUT_KEY);
    localStorage.removeItem(SESSION_ACTIVITY_KEY);
  };

  const refreshSession = async () => {
    try {
      await new Promise((resolve) => setTimeout(resolve, 100));
      resetTimer();
    } catch (error) {
      console.error('会话刷新失败:', error);
    }
  };

  const clearTimers = () => {
    if (activityTimer) {
      clearInterval(activityTimer);
      activityTimer = null;
    }
    if (warningTimer) {
      clearInterval(warningTimer);
      warningTimer = null;
    }
    if (refreshTimer) {
      clearInterval(refreshTimer);
      refreshTimer = null;
    }
  };

  const onWarning = (callback: (remaining: number) => void): (() => void) => {
    warningCallbacks.push(callback);
    return () => {
      const index = warningCallbacks.indexOf(callback);
      if (index > -1) {
        warningCallbacks.splice(index, 1);
      }
    };
  };

  const onExpired = (callback: () => void): void => {
    expiredCallbacks.push(callback);
  };

  const handleVisibilityChange = () => {
    if (document.visibilityState === 'visible') {
      const storedActivity = localStorage.getItem(SESSION_ACTIVITY_KEY);
      if (storedActivity) {
        const activityTime = parseInt(storedActivity, 10);
        if (Date.now() - activityTime > mergedConfig.timeout) {
          handleExpired();
        } else {
          lastActivity.value = activityTime;
        }
      }
    }
  };

  const handleUserActivity = () => {
    if (!isExpired.value) {
      resetTimer();
    }
  };

  onMounted(() => {
    const storedActivity = localStorage.getItem(SESSION_ACTIVITY_KEY);
    if (storedActivity) {
      lastActivity.value = parseInt(storedActivity, 10);
      const elapsed = Date.now() - lastActivity.value;

      if (elapsed >= mergedConfig.timeout) {
        handleExpired();
        return;
      }
    } else {
      updateActivity();
    }

    activityTimer = setInterval(checkSession, 1000);

    if (mergedConfig.refreshEnabled) {
      refreshTimer = setInterval(refreshSession, mergedConfig.refreshInterval);
    }

    document.addEventListener('visibilitychange', handleVisibilityChange);
    document.addEventListener('mousemove', handleUserActivity);
    document.addEventListener('keydown', handleUserActivity);
    document.addEventListener('click', handleUserActivity);
    document.addEventListener('scroll', handleUserActivity);
  });

  onUnmounted(() => {
    clearTimers();
    document.removeEventListener('visibilitychange', handleVisibilityChange);
    document.removeEventListener('mousemove', handleUserActivity);
    document.removeEventListener('keydown', handleUserActivity);
    document.removeEventListener('click', handleUserActivity);
    document.removeEventListener('scroll', handleUserActivity);
  });

  return {
    isExpired: readonly(isExpired),
    isWarning: readonly(isWarning),
    remainingTime: readonly(remainingTime),
    lastActivity: readonly(lastActivity),
    resetTimer,
    extendSession,
    destroySession,
    onWarning,
    onExpired,
  };
};
