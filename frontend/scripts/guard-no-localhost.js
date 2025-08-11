const fs = require('fs');
const path = require('path');

const buildRoot = path.resolve(__dirname, '../react/build');

const patterns = [
  /http:\/\/localhost/i,
  /127\.0\.0\.1/,
  /http:\/\/10\./i,
  /http:\/\/192\.168\./i,
  /http:\/\/172\.(1[6-9]|2[0-9]|3[0-1])\./i
];

function scanFile(file) {
  const text = fs.readFileSync(file, 'utf8');
  for (const re of patterns) {
    if (re.test(text)) {
      throw new Error(`Banned pattern ${re} found in ${file}`);
    }
  }
}

function walk(dir) {
  for (const name of fs.readdirSync(dir)) {
    const p = path.join(dir, name);
    const stat = fs.statSync(p);
    if (stat.isDirectory()) walk(p);
    else if (/\.(js|css|html|map)$/i.test(name)) scanFile(p);
  }
}

if (!fs.existsSync(buildRoot)) {
  console.error(`Build directory not found: ${buildRoot}`);
  process.exit(2);
}

walk(buildRoot);
console.log('CI guard passed: no localhost/RFC1918 strings found in build artifacts.');
