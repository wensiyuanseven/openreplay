

import { useState } from 'react';

export default function useToggle(defaultValue: boolean = false): [boolean, () => void, () => void, () => void] {
	const [value, setValue] = useState(defaultValue);
	const toggle = () => setValue(d => !d)
	const setFalse = () => setValue(false)
	const setTrue = () => setValue(true)
	return [value, toggle, setFalse, setTrue];
}

// 作用：这是一个自定义的 React Hook，用于管理布尔状态。它提供了布尔值的切换功能以及将状态设置为 true 或 false 的方法。
// 使用场景：适用于需要在两种状态之间切换的场景，如开关按钮、显示/隐藏元素、模态窗口等。开发者可以轻松管理布尔值状态的切换和设置。
// 注意点：
// 默认值为 false，可以根据需要传递初始值。
// 确保在逻辑上正确地调用 toggle, setFalse, 和 setTrue 函数，以避免状态混乱。