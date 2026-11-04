import { defineConfig } from '@playwright/test';
export default defineConfig({
 testDir:'./tests',workers:1,timeout:60000,
 use:{baseURL:'http://127.0.0.1:8765',headless:true,launchOptions:{executablePath:process.env.CHROME_PATH||'/usr/bin/google-chrome',args:['--no-sandbox']},viewport:{width:1440,height:1000}},
 webServer:{command:'cd ../backend && python -m uvicorn app.main:app --host 127.0.0.1 --port 8765',url:'http://127.0.0.1:8765/api/health',reuseExistingServer:false,env:{DATABASE_URL:`sqlite:////tmp/continuity-e2e-${process.pid}.db`,APP_ENV:'development'},timeout:30000},
 reporter:[['list'],['json',{outputFile:'test-results/results.json'}]],
});
