declare global {
  interface HTMLCanvasElement {
    captureStream(frameRate?: number): MediaStream;
  }
}

function dummyTrack(): MediaStreamTrack {
  const canvas = document.createElement('canvas'); //, { width: 0, height: 0})
  canvas.width = canvas.height = 2; // Doesn't work when 1 (?!)
  const ctx = canvas.getContext('2d');
  ctx?.fillRect(0, 0, canvas.width, canvas.height);
  requestAnimationFrame(function draw() {
    ctx?.fillRect(0, 0, canvas.width, canvas.height);
    requestAnimationFrame(draw);
  });
  // Also works. Probably it should be done once connected.
  //setTimeout(() => { ctx?.fillRect(0,0, canvas.width, canvas.height) }, 4000)
  return canvas.captureStream(60).getTracks()[0];
}

export function RequestLocalStream(): Promise<LocalStream> {
  return navigator.mediaDevices.getUserMedia({ audio: true }).then((aStream) => {
    const aTrack = aStream.getAudioTracks()[0];
    if (!aTrack) {
      throw new Error('No audio tracks provided');
    }
    return new _LocalStream(aTrack);
  });
}

class _LocalStream {
  private mediaRequested: boolean = false;
  readonly stream: MediaStream;
  private readonly vdTrack: MediaStreamTrack;

  constructor(aTrack: MediaStreamTrack) {
    this.vdTrack = dummyTrack();
    this.stream = new MediaStream([aTrack, this.vdTrack]);
  }

  toggleVideo(): Promise<boolean> {
    if (!this.mediaRequested) {
      return navigator.mediaDevices
        .getUserMedia({ video: true })
        .then((vStream) => {
          const vTrack = vStream.getVideoTracks()[0];
          if (!vTrack) {
            throw new Error('No video track provided');
          }
          this.stream.addTrack(vTrack);
          this.stream.removeTrack(this.vdTrack);
          this.mediaRequested = true;
          if (this.onVideoTrackCb) {
            this.onVideoTrackCb(vTrack);
          }
          return true;
        })
        .catch((e) => {
          // TODO: log
          console.error(e);
          return false;
        });
    }
    let enabled = true;
    this.stream.getVideoTracks().forEach((track) => {
      track.enabled = enabled = enabled && !track.enabled;
    });
    return Promise.resolve(enabled);
  }

  toggleAudio(): boolean {
    let enabled = true;
    this.stream.getAudioTracks().forEach((track) => {
      track.enabled = enabled = enabled && !track.enabled;
    });
    return enabled;
  }

  private onVideoTrackCb: ((t: MediaStreamTrack) => void) | null = null;

  onVideoTrack(cb: (t: MediaStreamTrack) => void) {
    this.onVideoTrackCb = cb;
  }

  stop() {
    this.stream.getTracks().forEach((t) => t.stop());
  }
}
// 类的兼容性：TypeScript 是结构化类型系统（structural typing），这意味着两个类型如果结构上兼容，那么它们可以互相赋值。所以，如果 _LocalStreaaaa 类的结构与 _LocalStream 相同或兼容（比如它实现了 _LocalStream 的所有方法和属性），那么可以将 new _LocalStreaaaa() 赋值给类型为 LocalStream 的变量。
// class _LocalStream {
//   start() {
//       console.log("Stream started");
//   }
//   stop() {
//       console.log("Stream stopped");
//   }
// }

// class _LocalStreaaaa {
//   start() {
//       console.log("New Stream started");
//   }
//   stop() {
//       console.log("New Stream stopped");
//   }
// }

// type LocalStream = InstanceType<typeof _LocalStream>;
// 是一种高级类型定义方式，用来基于现有的类或构造函数推导出其实例类型
// 这种方式在需要灵活处理类型推断或创建基于类实例的类型时非常有用。
// InstanceType<T> 是 TypeScript 中的一个内置泛型类型，它用来获取某个构造函数类型 T 所创建的实例的类型。
// 当你传入 typeof _LocalStream 时，InstanceType 会解析出 _LocalStream 这个类或构造函数所生成的实例的类型。
export type LocalStream = InstanceType<typeof _LocalStream>;
