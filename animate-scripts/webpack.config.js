const commandsDir = `${__dirname}/../auto-adobeanimate/animate-scripts-dist/`;

const path = require('path');
const fs = require('fs');

const entries = {};
fs.readdirSync(`${__dirname}/src/`).forEach((filename) => {
  if (!filename.endsWith('.js')) {
    return;
  }
  const name = filename.replace(/\.[^/.]+$/, "");
  const path = `${__dirname}/src/${filename}`;
  entries[name] = path;
})

module.exports = {
  entry: entries,
  output: {
    filename: '[name].jsfl',
    path: commandsDir
  },
  module: {
    rules: [
      {
        test: /\.tsx?|\.js$/,
        use: 'ts-loader',
        exclude: /node_modules/,
      },
    ],
  },
  resolve: {
    extensions: [ '.tsx', '.ts', '.js' ],
    modules: [
      path.resolve('./src'),
      path.resolve('./node_modules')
    ]
  },
  target: ['es3']
};