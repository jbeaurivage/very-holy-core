set projDir "./vivado"
set projName "very_holy_core"
set topName top
set device xc7a35tftg256-1
if {[file exists "$projDir"]} { file delete -force "$projDir" }
create_project $projName "$projDir" -part $device
set_property design_mode RTL [get_filesets sources_1]

# List of directories to search for .sv files
set sourceDirs [list "./target/veryl" "./target/veryl/memory"]

# Initialize empty list for all SystemVerilog files
set verilogSources [list]

# Find .sv files in each directory and append to the list
foreach dir $sourceDirs {
    # Check if directory exists before attempting to glob
    if {[file exists $dir] && [file isdirectory $dir]} {
        set dirFiles [glob -directory $dir -nocomplain -type f *.sv]
        foreach file $dirFiles {
            lappend verilogSources $file
        }
        puts "Added [llength $dirFiles] files from $dir"
    } else {
        puts "Warning: Directory $dir does not exist or is not a directory"
    }
}

add_files -fileset [get_filesets sources_1] -force -norecurse $verilogSources
set xdcSources [list "./fpga/alchrity_au/constraints.xdc" "./fpga/alchrity_au/au_props.xdc" ]
read_xdc $xdcSources
set_property STEPS.WRITE_BITSTREAM.ARGS.BIN_FILE true [get_runs impl_1]
update_compile_order -fileset sources_1
start_gui