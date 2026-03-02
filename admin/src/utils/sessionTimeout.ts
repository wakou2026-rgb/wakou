import { onMounted, onBeforeUnmount } from "vue";
import { useUserStoreHook } from "@/store/modules/user";

// Configuration constants
const INACTIVITY_TIMEOUT = 30 * 60 * 1000; // 30 minutes in milliseconds
const CHECK_INTERVAL = 60 * 1000; // Check every 60 seconds

let lastActivityTime = Date.now();
let timeoutCheckInterval: number | null = null;
let activityListeners: (() => void)[] = [];

/**
 * Composable for session timeout management.
 * Automatically logs out user after 30 minutes of inactivity.
 * Tracks activity via mousemove, keydown, and click events.
 */
export function useSessionTimeout() {
  const startTimer = () => {
    // Reset activity time on user interaction
    const updateActivity = () => {
      lastActivityTime = Date.now();
    };

    // Add event listeners for tracking user activity
    const events = ["mousemove", "keydown", "click"];
    events.forEach(event => {
      document.addEventListener(event, updateActivity);
      activityListeners.push(() => {
        document.removeEventListener(event, updateActivity);
      });
    });

    // Check for inactivity every 60 seconds
    timeoutCheckInterval = window.setInterval(() => {
      const now = Date.now();
      const inactiveTime = now - lastActivityTime;

      if (inactiveTime >= INACTIVITY_TIMEOUT) {
        stopTimer();
        // Session timeout - logout user
        useUserStoreHook().logOut();
      }
    }, CHECK_INTERVAL);
  };

  const stopTimer = () => {
    // Remove all activity listeners
    activityListeners.forEach(cleanup => cleanup());
    activityListeners = [];

    // Clear the interval
    if (timeoutCheckInterval !== null) {
      clearInterval(timeoutCheckInterval);
      timeoutCheckInterval = null;
    }
  };

  onMounted(() => {
    startTimer();
  });

  onBeforeUnmount(() => {
    stopTimer();
  });

  return {
    startTimer,
    stopTimer
  };
}
