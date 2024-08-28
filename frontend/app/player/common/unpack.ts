// fzstd: 如果你需要处理高压缩率、快速解压缩的 Zstandard（Zstd）压缩数据，fzstd 是一个合适的选择。Zstd 通常用于处理大规模数据集或需要高性能解压缩的场景。
// fflate: 适用于更常见的压缩格式如 gzip、zlib、ZIP，特别是当你需要在浏览器中处理这些压缩格式时。它的高性能和轻量级设计使其在前端应用中非常实用。
import * as fzstd from 'fzstd';
import { gunzipSync } from 'fflate';

const unpack = (b: Uint8Array): Uint8Array => {
  // zstd magical numbers 40 181 47 253
  const isZstd = b[0] === 0x28 && b[1] === 0xb5 && b[2] === 0x2f && b[3] === 0xfd;
  const isGzip = b[0] === 0x1f && b[1] === 0x8b && b[2] === 0x08;
  let data = b;
  if (isGzip) {
    const now = performance.now();
    const uData = gunzipSync(b);
    console.debug(
      'Gunzip time',
      Math.floor(performance.now() - now) + 'ms',
      'size',
      Math.floor(b.byteLength / 1024),
      '->',
      Math.floor(uData.byteLength / 1024),
      'kb'
    );
    data = uData;
  }
  if (isZstd) {
    const now = performance.now();
    const uData = fzstd.decompress(b);
    console.debug(
      'Zstd unpack time',
      Math.floor(performance.now() - now) + 'ms',
      'size',
      Math.floor(b.byteLength / 1024),
      '->',
      Math.floor(uData.byteLength / 1024),
      'kb'
    );
    data = uData;
  }
  return data;
};

export default unpack;
