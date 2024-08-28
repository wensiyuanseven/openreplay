import { useRef, useEffect } from 'react'


export default function useCancelableTimeout(
	onTimeout: () => void,
	onCancel: () => void,
	delay: number,
): [() => void, () => void] {
	const idRef = useRef<ReturnType<typeof setTimeout>>()
	const triggerTimeout = () => {
		clearTimeout(idRef.current)
		idRef.current = setTimeout(onTimeout, delay)
	}
	const cancelTimeout = () => {
		clearTimeout(idRef.current)
		onCancel()
	}
	useEffect(() => () => clearTimeout(idRef.current), []) // auto-cancel without callback (on clean)
	return [triggerTimeout, cancelTimeout]
}

// 作用：这是一个自定义的 React Hook，用于管理可取消的超时计时器。它提供了启动和取消超时的功能。
// 使用场景：适用于需要在一定时间后执行某个操作的场景，例如防抖、节流操作、用户输入后延迟执行某个任务等。特别是在组件卸载或某些条件下需要取消超时时很有用。
// 注意点：
// 在 useEffect 中确保清理超时计时器，以防止内存泄漏或意外的回调执行。
// 确保 onTimeout 和 onCancel 回调函数的依赖项不发生意外的变化，导致意外行为。