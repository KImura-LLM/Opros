const {Client} = require('ssh2');

function sshExec(cmd) {
  return new Promise((resolve, reject) => {
    const conn = new Client();
    conn.on('ready', () => {
      conn.exec(cmd, (err, stream) => {
        if (err) { reject(err); conn.end(); return; }
        let out = '';
        stream.on('data', d => { out += d.toString(); process.stdout.write(d); });
        stream.stderr.on('data', d => { out += d.toString(); process.stderr.write(d); });
        stream.on('close', () => { conn.end(); resolve(out); });
      });
    }).connect({host: '147.45.249.254', port: 22, username: 'root', password: 'u9*_.tnHfoESEt'});
  });
}

const SUDO_PASS = 'u9*_.tnHfoESEt';
const SSH_PASS = 'porol220088';

async function main() {
  const step = process.argv[2] || 'pull';
  
  if (step === 'pull') {
    console.log('=== Step 1: Git pull ===');
    await sshExec('cd /home/deploy/opros && git stash 2>/dev/null; git pull origin main 2>&1');
  } else if (step === 'build') {
    console.log('=== Step 2: Rebuild containers ===');
    await sshExec('cd /home/deploy/opros && docker compose -f docker-compose.prod.yml up -d --build backend nginx 2>&1');
  } else if (step === 'seed') {
    console.log('=== Step 3: Seed database ===');
    await sshExec('cd /home/deploy/opros && docker compose -f docker-compose.prod.yml exec -e PYTHONPATH=/app backend python -m scripts.seed --all 2>&1');
  } else if (step === 'status') {
    console.log('=== Check status ===');
    await sshExec('docker compose -f /home/deploy/opros/docker-compose.prod.yml ps 2>&1');
  } else if (step === 'logs') {
    console.log('=== Backend logs ===');
    await sshExec('docker compose -f /home/deploy/opros/docker-compose.prod.yml logs --tail=50 backend 2>&1');
  } else if (step === 'health') {
    console.log('=== Health check ===');
    await sshExec('curl -s http://localhost:8000/health 2>&1');
  }
}

main().catch(console.error);
