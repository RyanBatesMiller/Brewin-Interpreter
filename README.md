# Brewin-Interpreter

Project from CS 131 Fall Quarter 2023

## Introduction

Built interpreter for the dynamically-typed programming language Brewin#. Language supports objects with member fields, protocol inheritance, lambdas/closures, first-class functions, pass-by-reference, pass-by-value, type coercions, recursion, dynamic scoping, error handling.

### Using Brewin#

Creating a new object
```
func main() {
  a = @;    /* @ is the symbol for creating a new object */
  a.x = 10; /* adds a field called "x" to the object, sets value to 10 */
  print(a.x);  /* prints 10 */
}
```
