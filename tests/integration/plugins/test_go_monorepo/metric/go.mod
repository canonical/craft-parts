module example.com/test/metric

go 1.25

replace (
    example.com/test => ../
    example.com/test/core => ../core
)
