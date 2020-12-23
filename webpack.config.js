const commanddir = 'C:/Users/synthbot/AppData/Local/Adobe/Animate 2020/en_US/Configuration/Commands/'
// const commanddir = `${__dirname}/dist`;

const path = require('path');
const fs = require('fs');

const entries = {};
fs.readdirSync('./src/').forEach((filename) => {
  if (!filename.endsWith('.js')) {
    return;
  }
  const name = filename.replace(/\.[^/.]+$/, "");
  const path = `./src/${filename}`;
  entries[name] = path;
})

module.exports = {
  entry: entries,
  module: {
    rules: [
      {
        test: /\.m?js$/,
        exclude: /(node_modules|bower_components)/,
        use: {
          loader: 'babel-loader',
          options: {
            presets: ['@babel/preset-env']
          }
        }
      }
    ]
  },
  resolve: {
    extensions: [ '.js' ],
  },
  target: ['es5'],
  output: {
    filename: 'PPP_[name].jsfl',
    path: commanddir
  },
};