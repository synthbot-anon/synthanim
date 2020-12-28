const commanddir = 'C:/Users/synthbot/AppData/Local/Adobe/Animate 2020/en_US/Configuration/Commands/'
// const commanddir = `${__dirname}/dist`;

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
    filename: 'PPP_[name].jsfl',
    path: commanddir
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