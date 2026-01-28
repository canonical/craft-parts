cmake_minimum_required(VERSION 3.5)
project(package_cpp)

add_executable(mytest_cpp main.cpp)
install(TARGETS mytest_cpp DESTINATION bin)
