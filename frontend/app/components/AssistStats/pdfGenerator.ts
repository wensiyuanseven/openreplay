import { fileNameFormat } from 'App/utils';

export const getPdf2 = async () => {
  // @ts-ignore
  import('html2canvas').then(({ default: html2canvas }) => {
    // @ts-ignore
    window.html2canvas = html2canvas;

    // @ts-ignore
    import('jspdf').then(({ jsPDF }) => {
      const doc = new jsPDF('l', 'mm', 'a4');
      const now = new Date().toISOString();

      doc.addMetadata('Author', 'OpenReplay');
      doc.addMetadata('Title', 'OpenReplay Cobrowsing Report');
      doc.addMetadata('Subject', 'OpenReplay Cobrowsing Report');
      doc.addMetadata('Keywords', 'OpenReplay Cobrowsing Report');
      doc.addMetadata('Creator', 'OpenReplay');
      doc.addMetadata('Producer', 'OpenReplay');
      doc.addMetadata('CreationDate', now);
      // 类型断言的作用：
      // 规避严格的类型检查：有时候编译器无法确定一个值的类型是否符合预期，而你作为开发者知道这个类型是安全的。使用类型断言可以绕过编译器的严格类型检查。
      // 避免不必要的类型检查：当你确定某个操作或值是安全的，并且希望减少额外的类型检查时，类型断言可以帮助你简化代码。
      //
      // as 类型断言
      // 这是一个标准的 DOM API 调用，用于根据元素的 id 获取页面上的一个元素。
      // 它返回一个 HTMLElement | null，即可能返回一个 HTMLElement 对象，也可能返回 null（如果没有找到具有指定 id 的元素）。
      // 使用类型断言的前提：
      // 类型断言并不会改变运行时的行为或值本身，只是改变了 TypeScript 编译器在静态分析时对该值的类型认知。
      // 因此，在使用类型断言时，开发者需要非常确定断言是安全的，否则可能会导致运行时错误。例如，如果 getElementById 返回 null，但你用 as HTMLElement 将其断言为 HTMLElement，那么在使用 el 时就可能发生错误。
      const el = document.getElementById('pdf-anchor') as HTMLElement;

      function buildPng() {
        html2canvas(el, {
          scale: 2,
          ignoreElements: (e) => e.id.includes('pdf-ignore'),
        }).then((canvas) => {
          const imgData = canvas.toDataURL('img/png');

          let imgWidth = 290;
          let pageHeight = 200;
          let imgHeight = (canvas.height * imgWidth) / canvas.width;
          let heightLeft = imgHeight - pageHeight;
          let position = 0;
          const A4Height = 295;
          const headerW = 40;
          const logoWidth = 55;
          doc.addImage(imgData, 'PNG', 3, 10, imgWidth, imgHeight);

          doc.addImage('/assets/img/cobrowising-report-head.png', 'png', A4Height / 2 - headerW / 2, 2, 45, 5);
          if (position === 0 && heightLeft === 0)
            doc.addImage(
              '/assets/img/report-head.png',
              'png',
              imgWidth / 2 - headerW / 2,
              pageHeight - 5,
              logoWidth,
              5
            );

          while (heightLeft >= 0) {
            position = heightLeft - imgHeight;
            doc.addPage();
            doc.addImage(imgData, 'PNG', 5, position, imgWidth, imgHeight);
            doc.addImage(
              '/assets/img/report-head.png',
              'png',
              A4Height / 2 - headerW / 2,
              pageHeight - 5,
              logoWidth,
              5
            );
            heightLeft -= pageHeight;
          }

          doc.save(fileNameFormat('Assist_Stats_' + Date.now(), '.pdf'));
        });
      }

      buildPng();
    });
  });
};
