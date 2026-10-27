import { defineConfig, type Plugin } from "vite";
import react from "@vitejs/plugin-react-swc";
import path from "path";

const BACKEND = process.env.VERISENSE_BACKEND ?? "http://localhost:8001";

// Start only the current route's lazy modules during HTML parsing, instead of
// waiting for React -> portal -> page to discover the same module waterfall.
const initialRoutePreloads: Plugin = {
  name: "initial-route-preloads",
  apply: "build",
  transformIndexHtml: {
    order: "post",
    handler(_html, context) {
      const bundle = context.bundle ?? {};
      const chunks = Object.values(bundle).filter((item) => item.type === "chunk");
      const filesFor = (name: string) => {
        const root = chunks.find((chunk) => chunk.name === name);
        const files = new Set<string>();
        const visit = (fileName: string) => {
          const chunk = bundle[fileName];
          if (!chunk || chunk.type !== "chunk" || chunk.isEntry || files.has(fileName)) return;
          files.add(fileName);
          chunk.imports.forEach(visit);
        };
        if (root) visit(root.fileName);
        return [...files].map((file) => "/" + file);
      };
      const modules = Object.fromEntries(["SiteApp", "PortalApp", "AlertsPage", "DashboardPage", "ApplicationsPage", "ApplicationDetailPage", "InstitutionsPage"].map((name) => [name, filesFor(name)]));
      return [{
        tag: "script",
        injectTo: "head-prepend",
        attrs: { "data-route-preloads": true },
        children: `(function(){var m=${JSON.stringify(modules)},p=location.pathname,n=p.indexOf('/portal')===0?['PortalApp']:['SiteApp'];if(p==='/portal/alerts')n.push('AlertsPage');else if(p==='/portal/dashboard')n.push('DashboardPage');else if(/^\\/portal\\/(applications|my-applications)$/.test(p))n.push('ApplicationsPage');else if(/^\\/portal\\/applications\\/\\d+$/.test(p))n.push('ApplicationDetailPage');else if(p==='/portal/institutions')n.push('InstitutionsPage');var s=new Set();n.forEach(function(k){(m[k]||[]).forEach(function(h){if(s.has(h))return;s.add(h);var l=document.createElement('link');l.rel='modulepreload';l.href=h;l.crossOrigin='anonymous';document.head.appendChild(l);});});})();`,
      }];
    },
  },
};

// https://vitejs.dev/config/
export default defineConfig({
  server: {
    host: "0.0.0.0",
    port: 5176,
    proxy: {
      "/api": { target: BACKEND, changeOrigin: true },
      "/mock": { target: BACKEND, changeOrigin: true },
    },
  },
  preview: {
    port: 5176,
    proxy: {
      "/api": { target: BACKEND, changeOrigin: true },
      "/mock": { target: BACKEND, changeOrigin: true },
    },
  },
  plugins: [react(), initialRoutePreloads],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  build: {
    chunkSizeWarningLimit: 1200,
  },
});
