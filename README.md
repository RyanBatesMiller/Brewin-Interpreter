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

Adding and calling a method
```
func main() {
  a = @;
  a.x = 10;
  a.member_func = lambda(p) { 
    this.x = p;       /* sets a.x to value of p, using "this" keyword */
  };
  a.member_func(5);
  print(a.x);         /* prints 5 */
}

```

Support for protocol inheritence
```
func main() {
  /* define prototype object to represent an generic person */
  person = @;
  person.name = "anon";
  person.say_hi = lambda() { print(this.name," says hi!"); };

  carey = @;
  carey.proto = person;  /* assign person as carey's prototype object */

  carey.say_hi();        /* prints "anon says hi!" */
  carey.name = "Carey";
  carey.say_hi();        /* prints "Carey says hi!" */
}
```

Lambdas and Object closures
```
func main() {
  a = @;
  cap = 0;
  b = lambda() { cap = cap + 1; print(cap); };
  a.m = b;  /* points at same closure that b does */
  a.m();    /* prints 1 */
  a.m();    /* prints 2 */
  b();      /* prints 3, since a.m and b point to same closure  */
}
```

Object comparisons
```
func main() {
  x = @;
  x.a = 10;
  z = x;
  y = @;
  y.a = 10;

  if (x == x && x == z) { print("This will print out!"); }
  if (x == y) { print("This will not print!"); }
}
```

Variables captured by closures (by reference)
```
func main() {
 c = @;
 /* d captures object c by object reference */ 
 d = lambda() { c.x = 5; };

 d();  
 print(c.x);  /* prints 5, since closure modified original object */
}
```
```
func main() {
 c = @;
 c.x = 5;

 /* d captures object c by object reference */
 d = lambda() {
   c = @;  /* changes original c variable, pointing it at a new obj */
   c.y = 10; /* adds field y to updated object */
 };

 d();
 print(c.y); /* prints 10 */
 print(c.x); /* NAME_ERROR since our original object is gone! */
}
```



