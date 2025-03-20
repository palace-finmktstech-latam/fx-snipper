const { contextBridge } = require('electron');

// Expose safe Electron APIs to the renderer process
contextBridge.exposeInMainWorld('electronAPI', {
  // Add any APIs you want to expose in the future
});
