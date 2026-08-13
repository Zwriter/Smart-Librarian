const { execSync, spawn } = require('node:child_process');
const readline = require('node:readline');

const npmCommand = process.platform === 'win32' ? 'npm.cmd' : 'npm';

function ask(question) {
  const interface = readline.createInterface({
    input: process.stdin,
    output: process.stdout,
  });

  return new Promise((resolve) => {
    interface.question(question, (answer) => {
      interface.close();
      resolve(answer.trim().toLowerCase());
    });
  });
}

async function main() {
  try {
    execSync(`${npmCommand} test`, { stdio: 'inherit' });
  } catch {
    process.exit(1);
  }

  console.clear();
  const answer = await ask('\nAll tests passed. Start the development servers? [Y/n] ');

  if (answer && answer !== 'y' && answer !== 'yes') {
    console.log('Development servers were not started.');
    return;
  }

  const servers = process.platform === 'win32'
    ? spawn(process.env.ComSpec || 'cmd.exe', ['/d', '/s', '/c', 'npm run dev:servers'], {
        stdio: 'inherit',
      })
    : spawn('npm', ['run', 'dev:servers'], {
        stdio: 'inherit',
      });

  process.on('SIGINT', () => servers.kill('SIGINT'));
  process.on('SIGTERM', () => servers.kill('SIGTERM'));
  servers.on('exit', (code) => process.exit(code ?? 0));
}

main();