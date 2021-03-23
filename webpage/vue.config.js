// Ref: https://cli.vuejs.org/config/#outputdir
//

module.exports = {
	devServer: {
		proxy: {
			"^/(api)": {
				target: "http://localhost:17310",
				ws: true,
				changeOrigin: true,
			}
		}
	},
	publicPath: "/static/webpack/",
	outputDir: "../weditor/static/webpack/",
	indexPath: "../../templates/index2.html" // path relative to outputDir
}
