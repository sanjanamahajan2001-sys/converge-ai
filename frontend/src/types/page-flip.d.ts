declare module 'page-flip' {
  export interface PageFlipSettings {
    startPage?: number;
    size?: 'fixed' | 'stretch';
    width: number;
    height: number;
    minWidth?: number;
    maxWidth?: number;
    minHeight?: number;
    maxHeight?: number;
    drawShadow?: boolean;
    flippingTime?: number;
    usePortrait?: boolean;
    startZIndex?: number;
    autoSize?: boolean;
    maxShadowOpacity?: number;
    showCover?: boolean;
    mobileScrollSupport?: boolean;
    clickEventForward?: boolean;
    useMouseEvents?: boolean;
    swipeDistance?: number;
    showPageCorners?: boolean;
    disableFlipByClick?: boolean;
  }

  export interface PageFlipEvent {
    data: any;
    object: PageFlip;
  }

  export class PageFlip {
    constructor(element: HTMLElement, settings: PageFlipSettings);
    loadFromHTML(items: NodeListOf<HTMLElement> | HTMLElement[]): void;
    loadFromImages(imagesHref: string[]): void;
    updateFromHtml(items: NodeListOf<HTMLElement> | HTMLElement[]): void;
    updateFromImages(imagesHref: string[]): void;
    update(): void;
    destroy(): void;
    clear(): void;
    turnToPrevPage(): void;
    turnToNextPage(): void;
    turnToPage(pageNum: number): void;
    flipNext(corner?: 'top' | 'bottom'): void;
    flipPrev(corner?: 'top' | 'bottom'): void;
    flip(pageNum: number, corner?: 'top' | 'bottom'): void;
    getPageCount(): number;
    getCurrentPageIndex(): number;
    getPage(pageIndex: number): {
      setDensity: (density: 'soft' | 'hard') => void;
      getElement?: () => HTMLElement;
    };
    getOrientation(): 'portrait' | 'landscape';
    getState(): 'user_fold' | 'fold_corner' | 'flipping' | 'read';
    on(eventName: 'flip' | 'changeOrientation' | 'changeState' | 'init' | 'update', callback: (e: PageFlipEvent) => void): PageFlip;
    off(eventName: string): void;
  }
}
