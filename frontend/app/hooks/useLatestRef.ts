import { useRef, useEffect } from 'react'


export default function useLatestRef<T>(state: T) {
  const ref = useRef<T>(state)
  useEffect(() => { ref.current = state }, [ state ])
  return ref
}


// 作用：这是一个自定义的 React Hook，用于创建一个始终保持最新状态的引用（ref）。它将传入的状态 state 保持在一个 ref 对象中，并在状态变化时更新该 ref。
// 使用场景：适用于需要访问最新状态的场景，而不触发重新渲染的情况下。常用于异步回调中，需要使用最新状态但不希望因为状态变化而重新渲染组件。
// 注意点：
// 确保 useLatestRef 仅用于需要引用最新状态的场景，而不是直接在组件渲染中使用状态。
// 适当管理依赖项，以确保 ref 在正确的时间点被更新。