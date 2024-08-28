// 作用：这是一个自定义的 React Hook，用于创建 CellMeasurerCache 的实例，这个实例来自 react-virtualized 库，用于优化虚拟化列表中单元格的测量和渲染。
// 使用场景：适用于需要渲染大量数据的虚拟化列表的场景，通过缓存单元格的测量结果来提高渲染性能，尤其是在动态内容高度的情况下。
// 注意点：
// useMemo 确保 CellMeasurerCache 只在组件挂载时创建一次，避免不必要的重新计算。
// 确保在 options 参数中正确传递 CellMeasurerCacheParams，以适应特定的列表渲染需求。
// 如果列表内容的大小或布局发生了重大变化，可能需要手动清除或重置缓存。
import { useMemo } from 'react'
import { CellMeasurerCache, CellMeasurerCacheParams } from 'react-virtualized';

export default function useCellMeasurerCache(options?: CellMeasurerCacheParams) {
  return useMemo(() => new CellMeasurerCache({
    fixedWidth: true,
    ...options
  }), [])
}