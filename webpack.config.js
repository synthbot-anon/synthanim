// const commandsDir = 'C:/Users/synthbot/AppData/Local/Adobe/Animate 2020/en_US/Configuration/Commands/'
const commandsDir = `${__dirname}/dist`;

const path = require('path');
const fs = require('fs');

const entries = {};
fs.readdirSync(`${__dirname}/src/jsfl/`).forEach((filename) => {
  if (!filename.endsWith('.js')) {
    return;
  }
  const name = filename.replace(/\.[^/.]+$/, "");
  const path = `${__dirname}/src/jsfl/${filename}`;
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
      path.resolve('./src/jsfl'),
      path.resolve('./node_modules')
    ]
  },
  target: ['es3']
};