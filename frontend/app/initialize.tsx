import './styles/index.scss'; //引入全局样式文件
import React from 'react'; //引入 React 库，允许使用 JSX 和 React 组件。
// createRoot 的主要作用是创建一个根容器，并在该容器上渲染 React 组件。好处 【分片渲染，切片渲染】
import { createRoot } from 'react-dom/client';  //React 18 的新 API，用于创建应用程序的根节点并在其上渲染 React 组件
import './init';  //引入项目的初始化逻辑
import { Provider } from 'react-redux';  //使得应用中所有组件可以访问 Redux Store。
import store from './store';
import Router from './Router';
import { StoreProvider, RootStore } from './mstore';
import { HTML5Backend } from 'react-dnd-html5-backend'; //react-dnd的库，用于实现拖拽和放置功能，HTML5Backend 是拖拽操作的后端实现。
import { DndProvider } from 'react-dnd'; //react-dnd的库，用于实现拖拽和放置功能，HTML5Backend 是拖拽操作的后端实现。
import { ConfigProvider, theme, ThemeConfig } from 'antd';  //用于提供主题配置和定制组件样式。
import colors from 'App/theme/colors';  //引入自定义的颜色配置文件，用于主题的颜色定义。
import { BrowserRouter } from 'react-router-dom';  //从 react-router-dom 库中引入 BrowserRouter，用于处理基于浏览器的路由
import { Notification, MountPoint } from 'UI';  //用于全局通知和应用中其他的功能挂载点

// @ts-ignore
window.getCommitHash = () => console.log(window.env.COMMIT_HASH);

// 定义了自定义的主题配置，定制了 antd 组件的颜色、背景、字体、按钮等外观。这使得整个应用的风格可以根据定义的颜色变量和其他样式进行统一的定制。
const customTheme: ThemeConfig = {
  // algorithm: theme.compactAlgorithm,
  components: {
    Layout: {
      headerBg: colors['gray-lightest'],
      siderBg: colors['gray-lightest']
    },
    Segmented: {
      itemSelectedBg: '#FFFFFF',
      itemSelectedColor: colors['main'],
    },
    Menu: {
      colorPrimary: colors.teal,
      colorBgContainer: colors['gray-lightest'],
      colorFillTertiary: colors['gray-lightest'],
      colorBgLayout: colors['gray-lightest'],
      subMenuItemBg: colors['gray-lightest'],

      itemHoverBg: colors['active-blue'],
      itemHoverColor: colors['teal'],

      itemActiveBg: colors['active-blue'],
      itemSelectedBg: colors['active-blue'],
      itemSelectedColor: colors['teal'],

      itemMarginBlock: 0,
      itemPaddingInline: 50,
      iconMarginInlineEnd: 14,
      collapsedWidth: 180,
    },
    Button: {
      colorPrimary: colors.teal
    }
  },
  token: {
    colorPrimary: colors.teal,
    colorPrimaryActive: '#394EFF',
    colorBgLayout: colors['gray-lightest'],
    colorBgContainer: colors['white'],
    colorLink: colors['teal'],
    colorLinkHover: colors['teal-dark'],

    borderRadius: 4,
    fontSize: 14,
    fontFamily: '\'Roboto\', \'ArialMT\', \'Arial\''
  }
};

// 当 DOM 加载完成时执行该函数，确保页面元素（如 #app）已经准备好
document.addEventListener('DOMContentLoaded', () => {
  const container = document.getElementById('app');
  // @ts-ignore
  // 使用 React 18 的 createRoot 方法创建应用的根节点。
  const root = createRoot(container);

  // const theme = window.localStorage.getItem('theme');
  // 使用 root.render 方法渲染React组件树，这里可以是任何有效的 React 组件。
  root.render(
    <ConfigProvider theme={customTheme}>
      {/* Provider 使得应用中的所有组件都可以通过 connect 函数、useSelector 和 useDispatch 钩子访问 Redux store，
      而无需手动将 store 传递到每个组件中。 */}
      <Provider store={store}>
        <StoreProvider store={new RootStore()}>
          <DndProvider backend={HTML5Backend}>
            <BrowserRouter>
              <Notification />
              <Router />
            </BrowserRouter>
          </DndProvider>
          <MountPoint />
        </StoreProvider>
      </Provider>
    </ConfigProvider>
  );
});
