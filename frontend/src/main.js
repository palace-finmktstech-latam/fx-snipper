const { app, BrowserWindow, screen } = require('electron');
const path = require('path');

function createWindow() {
  const { width, height } = screen.getPrimaryDisplay().workAreaSize;

  const mainWindow = new BrowserWindow({
    width: 400,
    height: 600,
    x: width - 400,
    y: 0,
    webPreferences: {
      nodeIntegration: true,
      contextIsolation: true,
      webSecurity: true
    },
    //alwaysOnTop: true,
    icon: path.join(__dirname, '../public/favicon.jpg')
  });

  mainWindow.setMenu(null);

  // Set CSP headers before loading the file
  mainWindow.webContents.session.webRequest.onHeadersReceived((details, callback) => {
    callback({
      responseHeaders: {
        ...details.responseHeaders,
        'Content-Security-Policy': ["default-src 'self' 'unsafe-inline' 'unsafe-eval' blob: data: file:; img-src 'self' blob: data: file:; font-src 'self' data: file:; style-src 'self' 'unsafe-inline'; connect-src 'self' http://localhost:5001 file:*"],
        'Access-Control-Allow-Origin': ['*']
      }
    });
  });

  // Remove any existing CSP meta tags from the HTML
  mainWindow.webContents.on('dom-ready', () => {
    mainWindow.webContents.executeJavaScript(`
      const metaTags = document.getElementsByTagName('meta');
      for (let i = metaTags.length - 1; i >= 0; i--) {
        if (metaTags[i].httpEquiv === 'Content-Security-Policy') {
          metaTags[i].remove();
        }
      }
    `);
  });

  mainWindow.loadFile(path.join(__dirname, '../public/index.html'));
  //mainWindow.webContents.openDevTools();
  mainWindow.webContents.setZoomFactor(1);
}

app.whenReady().then(createWindow);

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

app.on('activate', () => {
  if (BrowserWindow.getAllWindows().length === 0) {
    createWindow();
  }
});