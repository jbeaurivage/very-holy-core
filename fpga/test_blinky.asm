# Led blinky
.section .text
.align 2
.global _start

start:
    # Init
    li x6, 0x80000000 # GPIO base address x6 <= 0x80000000
    addi x18, x0, 0 # Set LED counter to 0

loop:
    addi x18, x18, 0x1 # Increment LED counter
    sb x18, 0(x6) # Write new counter to GPIO base addr
    li x21, 4000000 # delay counter

delay_loop:
    addi x21, x21, -1
    bnez x21, delay_loop

    j loop
