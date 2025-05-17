
import * as React from "react";
import { useIsMobile } from "./use-mobile";

type TouchEvents = {
  lastY: number;
  scrollingUp: boolean;
  hideUiOnScroll: boolean;
};

export function useTouchEvents() {
  const isMobile = useIsMobile();
  const [touchEvents, setTouchEvents] = React.useState<TouchEvents>({
    lastY: 0,
    scrollingUp: false,
    hideUiOnScroll: false,
  });

  React.useEffect(() => {
    if (!isMobile) return;

    const handleTouchStart = (e: TouchEvent) => {
      setTouchEvents(prev => ({
        ...prev,
        lastY: e.touches[0].clientY
      }));
    };

    const handleTouchMove = (e: TouchEvent) => {
      const currentY = e.touches[0].clientY;
      const scrollingUp = currentY > touchEvents.lastY;
      
      setTouchEvents(prev => ({
        ...prev,
        lastY: currentY,
        scrollingUp,
        hideUiOnScroll: !scrollingUp && window.scrollY > 50
      }));
    };

    const handleScroll = () => {
      if (window.scrollY < 10) {
        setTouchEvents(prev => ({
          ...prev,
          hideUiOnScroll: false
        }));
      }
    };

    document.addEventListener('touchstart', handleTouchStart);
    document.addEventListener('touchmove', handleTouchMove);
    window.addEventListener('scroll', handleScroll);

    return () => {
      document.removeEventListener('touchstart', handleTouchStart);
      document.removeEventListener('touchmove', handleTouchMove);
      window.removeEventListener('scroll', handleScroll);
    };
  }, [isMobile, touchEvents.lastY]);

  return touchEvents;
}
