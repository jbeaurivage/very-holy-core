alias t := test
alias b := build
alias c := check

vivado:
	veryl build --quiet
	vivado -nolog -nojournal -mode tcl -source {{justfile_directory()}}/init_project.tcl

wave file:
	surfer {{justfile_directory()}}/target/waveform/{{file}}.vcd >& /dev/null & 

build:
	veryl build --quiet

check:
	veryl check --quiet

fmt:
	veryl fmt --quiet

test TEST *extra_args:
	veryl test {{justfile_directory()}}/src/tests/test_{{TEST}}.veryl \
		{{justfile_directory()}}/src/*.veryl \
		{{justfile_directory()}}/src/peripherals/*.veryl \
		{{justfile_directory()}}/src/cpu/*.veryl \
		{{justfile_directory()}}/src/memory/*.veryl \
		{{justfile_directory()}}/src/cpu/load_store/*.veryl \
		{{justfile_directory()}}/src/cpu/writeback/*.veryl \
		--wave --quiet {{extra_args}}