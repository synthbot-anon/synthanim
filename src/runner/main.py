# startserver
# launch browser interface

# scan for available clips
# scan for completed clips
# get a job list

# for each job item
# ... run the job
# ... monitor for any issues
# ... skip the file if needed
# ... add completed files to an -in-progress.zip zip archive
# ... create new archive every X00 MB

# interface can
# ... show status
# ... whitelist/blacklist jobs to process
# ... prioritize jobs to process


from animate_interface import AnimateInterface

animate = AnimateInterface("C:/Program Files/Adobe/Adobe Animate 2021/animate.exe")
output = animate.run_script(
	"C:/Users/synthbot/jsfl/dist/OpenAnimate.jsfl",
	input='testing123'
)

for msg in output:
	print(msg)