// Convierte los HTML de esta carpeta en PDF tamaño carta:  node prospectos/auditorias/a-pdf.js
const { chromium } = require('playwright');
const path = require('path');
(async () => {
  const b = await chromium.launch();
  for (const n of ['hojas-para-entregar', 'guia-del-fundador']) {
    const p = await b.newPage();
    await p.goto('file://' + path.join(__dirname, n + '.html'));
    await p.pdf({ path: path.join(__dirname, n + '.pdf'), format: 'Letter', printBackground: true, preferCSSPageSize: true });
    await p.close();
  }
  await b.close();
  console.log('PDF generados');
})();
