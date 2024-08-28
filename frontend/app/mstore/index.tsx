// 这个文件定义了一个 React 应用中的全局状态管理系统，特别是基于 RootStore 的 MobX 或类似架构的状态管理。
// 它提供了一个上下文 (StoreContext)，通过这个上下文可以在整个应用中访问和使用不同的 store。
import React from 'react';
import DashboardStore from './dashboardStore';
import MetricStore from './metricStore';
import UserStore from './userStore';
import RoleStore from './roleStore';
import APIClient from 'App/api_client';
import FunnelStore from './funnelStore';
import { services } from 'App/services';
import SettingsStore from './settingsStore';
import AuditStore from './auditStore';
import NotificationStore from './notificationStore';
import ErrorStore from './errorStore';
import SessionStore from './sessionStore';
import NotesStore from './notesStore';
import RecordingsStore from './recordingsStore';
import AssistMultiviewStore from './assistMultiviewStore';
import WeeklyReportStore from './weeklyReportConfigStore';
import AlertStore from './alertsStore';
import FeatureFlagsStore from './featureFlagsStore';
import UxtestingStore from './uxtestingStore';
import TagWatchStore from './tagWatchStore';
import AiSummaryStore from "./aiSummaryStore";
import AiFiltersStore from "./aiFiltersStore";

// RootStore 类是整个应用的状态管理中心，它汇集了多个子 store，每个 store 负责管理应用的不同部分的状态。
export class RootStore {
  // TODO语法
  dashboardStore: DashboardStore;
  metricStore: MetricStore;
  funnelStore: FunnelStore;
  settingsStore: SettingsStore;
  userStore: UserStore;
  roleStore: RoleStore;
  auditStore: AuditStore;
  errorStore: ErrorStore;
  notificationStore: NotificationStore;
  sessionStore: SessionStore;
  notesStore: NotesStore;
  recordingsStore: RecordingsStore;
  assistMultiviewStore: AssistMultiviewStore;
  weeklyReportStore: WeeklyReportStore;
  alertsStore: AlertStore;
  featureFlagsStore: FeatureFlagsStore;
  uxtestingStore: UxtestingStore;
  tagWatchStore: TagWatchStore;
  aiSummaryStore: AiSummaryStore;
  aiFiltersStore: AiFiltersStore;

  // 在 constructor 方法中，RootStore 实例化了所有的子 store，例如 DashboardStore、MetricStore、UserStore 等。
  // 这些子 store 管理特定功能模块的状态和逻辑。

  constructor() {
    this.dashboardStore = new DashboardStore();
    this.metricStore = new MetricStore();
    this.funnelStore = new FunnelStore();
    this.settingsStore = new SettingsStore();
    this.userStore = new UserStore();
    this.roleStore = new RoleStore();
    this.auditStore = new AuditStore();
    this.errorStore = new ErrorStore();
    this.notificationStore = new NotificationStore();
    this.sessionStore = new SessionStore();
    this.notesStore = new NotesStore();
    this.recordingsStore = new RecordingsStore();
    this.assistMultiviewStore = new AssistMultiviewStore();
    this.weeklyReportStore = new WeeklyReportStore();
    this.alertsStore = new AlertStore();
    this.featureFlagsStore = new FeatureFlagsStore();
    this.uxtestingStore = new UxtestingStore();
    this.tagWatchStore = new TagWatchStore();
    this.aiSummaryStore = new AiSummaryStore();
    this.aiFiltersStore = new AiFiltersStore();
  }

  initClient() {
    // initClient 方法创建一个新的 APIClient 实例，并将其传递给应用的各个服务模块 (services)。
    // 这个方法的目的是确保每个服务模块都能共享同一个 APIClient 实例，从而在应用中统一管理 API 调用。
    const client = new APIClient();
    services.forEach((service) => {
      service.initClient(client);
    });
  }
}
// StoreContext 是通过 React.createContext 创建的 React 上下文对象，用于在应用的不同组件之间共享 RootStore 实例。
// 这个上下文允许在组件树的任意深度访问 RootStore，而不需要通过组件层层传递。
const StoreContext = React.createContext<RootStore>({} as RootStore);

export const StoreProvider = ({ children, store }: any) => {
  return <StoreContext.Provider value={store}>{children}</StoreContext.Provider>;
};

export const useStore = () => React.useContext(StoreContext);

export const withStore = (Component: any) => (props: any) => {
  return <Component {...props} mstore={useStore()} />;
};
