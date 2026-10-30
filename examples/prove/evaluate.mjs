import { pathToFileURL } from 'node:url';
let request = '';
for await (const chunk of process.stdin) request += chunk;
const { artifact, input } = JSON.parse(request);
const parse = (await import(pathToFileURL(artifact))).default;
const actual = parse(input.text);
console.log(JSON.stringify({ checks: [{
  id: 'values', passed: JSON.stringify(actual) === JSON.stringify(input.expected),
  evidence: `Actual ${JSON.stringify(actual)}; expected ${JSON.stringify(input.expected)}`,
}] }));
