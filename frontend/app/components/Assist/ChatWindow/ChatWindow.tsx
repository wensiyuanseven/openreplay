import React, { useState, useEffect } from 'react';
import VideoContainer from '../components/VideoContainer';
import cn from 'classnames';
import Counter from 'App/components/shared/SessionItem/Counter';
import stl from './chatWindow.module.css';
import ChatControls from '../ChatControls/ChatControls';
import Draggable from 'react-draggable';
import type { LocalStream } from 'Player';
import { PlayerContext } from 'App/components/Session/playerContext';

// 在 TypeScript 中，当你在代码中使用 MediaStream 时，无需显式地导入它，这是因为 MediaStream 是一个全局定义的类型。
// TypeScript 自动包含了一些标准的类型定义库，特别是与浏览器环境相关的库，比如 lib.dom.d.ts。
// 这个文件中包含了浏览器的各种内置对象的类型定义，包括 MediaStream。
// 具体说明：
// 全局类型定义：MediaStream 属于浏览器环境下的全局对象。
// TypeScript 在编译时会自动加载标准库中的类型定义，包括所有的 DOM API 和 Web API 类型。
// 因此，像 MediaStream 这样常见的接口不需要手动导入就可以直接使用。
// lib.dom.d.ts：这是 TypeScript 内置的一部分类型定义文件，专门为浏览器提供的 API 定义类型。
// 例如，MediaStream、Document、Window 等都是在这个文件中定义的。
export interface Props {
  incomeStream: MediaStream[] | null;
  localStream: LocalStream | null;
  userId: string;
  isPrestart?: boolean;
  endCall: () => void;
}

function ChatWindow({ userId, incomeStream, localStream, endCall, isPrestart }: Props) {
  const { player } = React.useContext(PlayerContext)

  const toggleVideoLocalStream = player.assistManager.toggleVideoLocalStream;

  const [localVideoEnabled, setLocalVideoEnabled] = useState(false);
  const [anyRemoteEnabled, setRemoteEnabled] = useState(false);

  const onlyLocalEnabled = localVideoEnabled && !anyRemoteEnabled;

  useEffect(() => {
    toggleVideoLocalStream(localVideoEnabled)
  }, [localVideoEnabled])

  return (
    <Draggable handle=".handle" bounds="body" defaultPosition={{ x: 50, y: 200 }}>
      <div
        className={cn(stl.wrapper, 'fixed radius bg-white shadow-xl mt-16')}
        style={{ width: '280px' }}
      >
        <div className="handle flex items-center p-2 cursor-move select-none border-b">
          <div className={stl.headerTitle}>
            <b>Call with </b> {userId ? userId : 'Anonymous User'}
            <br />
            {incomeStream && incomeStream.length > 2 ? ' (+ other agents in the call)' : ''}
          </div>
          <Counter startTime={new Date().getTime()} className="text-sm ml-auto" />
        </div>
        <div
          className={cn(stl.videoWrapper, 'relative')}
          style={{ minHeight: onlyLocalEnabled ? 210 : 'unset' }}
        >
          {incomeStream ? (
            incomeStream.map((stream) => (
              <React.Fragment key={stream.id}>
                <VideoContainer stream={stream} setRemoteEnabled={setRemoteEnabled} />
              </React.Fragment>
            ))
          ) : (
            <div className={stl.noVideo}>Error obtaining incoming streams</div>
          )}
          <div className={cn('absolute bottom-0 right-0 z-50', localVideoEnabled ? '' : '!hidden')}>
            <VideoContainer
              stream={localStream ? localStream.stream : null}
              muted
              height={anyRemoteEnabled ? 50 : 'unset'}
            />
          </div>
        </div>
        <ChatControls
          videoEnabled={localVideoEnabled}
          setVideoEnabled={setLocalVideoEnabled}
          stream={localStream}
          endCall={endCall}
          isPrestart={isPrestart}
        />
      </div>
    </Draggable>
  );
}

export default ChatWindow;
