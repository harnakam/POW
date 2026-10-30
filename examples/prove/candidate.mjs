export default (text) => text === '' ? [] : text.split(',').map(Number);
