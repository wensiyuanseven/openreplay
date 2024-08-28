import { useState } from 'react';

export default function useForceUpdate() {
    const [value, setValue] = useState(0);
    return () => setValue(value => value + 1);
}

// 作用：这是一个自定义的 React Hook，用于强制组件重新渲染。它通过更新一个本地状态的值来触发组件的重新渲染。
// 使用场景：适用于需要手动触发组件重新渲染的场景，例如在不依赖于状态变化的情况下强制更新组件视图。通常用于处理一些 React 不会自动重新渲染的场景。
// 注意点：
// 使用 useForceUpdate 时要小心，因为强制渲染可能会导致性能问题或不必要的重新渲染。
// 确保只在必要的情况下使用此 Hook，以避免潜在的性能问题。