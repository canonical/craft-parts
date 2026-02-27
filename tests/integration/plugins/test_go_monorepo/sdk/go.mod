module example.com/test/sdk

go 1.25

replace (
    example.com/test => ../
    example.com/test/core => ../core
    example.com/test/trace => ../trace
    example.com/test/metric => ../metric
)
