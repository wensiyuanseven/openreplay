import { useRef, useEffect, useCallback } from 'react'

export default function useIsMounted(): () => boolean {
    const ref = useRef(false);

    useEffect(() => {
        ref.current = true;
        return () => {
        ref.current = false;
        };
    }, []);

    return useCallback(() => ref.current, [ref]);
}



// 作用：这是一个自定义的 React Hook，用于检查组件是否已挂载。它返回一个函数，该函数在组件挂载时返回 true，在卸载时返回 false。
// 使用场景：适用于需要检测组件是否仍然挂载的异步操作场景，以避免在组件卸载后尝试更新状态，导致内存泄漏或不必要的错误。
// 注意点：
// 确保在异步操作或定时器中使用此 Hook 来防止组件卸载后的状态更新。
// 避免在没有必要的情况下使用它，因为这可能导致不必要的性能开销。
