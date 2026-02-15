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
    }).connect({host: '147.45.249.254', port: 22, username: 'deploy', password: 'porol220088'});
  });
}

async function main() {
  const step = process.argv[2] || 'pull';
  
  if (step === 'pull') {
    console.log('=== Step 1: Git stash + pull ===');
    await sshExec('echo porol220088 | sudo -S bash -c "cd /home/deploy/opros && git stash && git pull origin main"');
  } else if (step === 'build') {
    console.log('=== Step 2: Rebuild containers ===');
    await sshExec('echo porol220088 | sudo -S bash -c "cd /home/deploy/opros && docker compose -f docker-compose.prod.yml up -d --build backend nginx"');
  } else if (step === 'seed') {
    console.log('=== Step 3: Seed database ===');
    await sshExec('echo porol220088 | sudo -S bash -c "cd /home/deploy/opros && docker compose -f docker-compose.prod.yml exec -e PYTHONPATH=/app backend python -m scripts.seed --all"');
  } else if (step === 'status') {
    console.log('=== Check status ===');
    await sshExec('echo porol220088 | sudo -S docker compose -f /home/deploy/opros/docker-compose.prod.yml ps');
  } else if (step === 'logs') {
    console.log('=== Backend logs ===');
    await sshExec('echo porol220088 | sudo -S docker compose -f /home/deploy/opros/docker-compose.prod.yml logs --tail=30 backend');
  }
}

main().catch(console.error);
