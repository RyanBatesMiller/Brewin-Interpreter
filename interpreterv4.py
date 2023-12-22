import copy
from enum import Enum

from brewparse import parse_program
from env_v2 import EnvironmentManager
from intbase import InterpreterBase, ErrorType
from type_valuev2 import Type, Value, create_value, get_printable
from lambda_class import Lambda
from object_class import Object

class ExecStatus(Enum):
    CONTINUE = 1
    RETURN = 2
    
# Main interpreter class
class Interpreter(InterpreterBase):
    # constants
    NIL_VALUE = create_value(InterpreterBase.NIL_DEF)
    TRUE_VALUE = create_value(InterpreterBase.TRUE_DEF)
    BIN_OPS = {"+", "-", "*", "/", "==", "!=", ">", ">=", "<", "<=", "||", "&&"}

    # methods
    def __init__(self, console_output=True, inp=None, trace_output=False):
        super().__init__(console_output, inp)
        self.trace_output = trace_output
        self.__setup_ops()
        self.curr_obj = None
        self.referenced_names = []
        self.closures = {}

    # run a program that's provided in a string
    # usese the provided Parser found in brewparse.py to parse the program
    # into an abstract syntax tree (ast)
    def run(self, program):
        ast = parse_program(program)
        self.__set_up_function_table(ast)
        self.env = EnvironmentManager()
        main_func = self.__get_func_by_name("main", 0)
        self.__run_statements(main_func.get("statements"))

    def __set_up_function_table(self, ast):
        self.func_name_to_ast = {}
        for func_def in ast.get("functions"):
            func_name = func_def.get("name")
            num_params = len(func_def.get("args"))
            if func_name not in self.func_name_to_ast:
                self.func_name_to_ast[func_name] = {}
            self.func_name_to_ast[func_name][num_params] = func_def

    def __get_func_by_name(self, name, num_params):
        if name not in self.func_name_to_ast:
            super().error(ErrorType.NAME_ERROR, f"Function {name} not found")
        candidate_funcs = self.func_name_to_ast[name]
        if num_params not in candidate_funcs:
            super().error(
                ErrorType.NAME_ERROR,
                f"Function {name} taking {num_params} params not found",
            )
        return candidate_funcs[num_params]

    def __run_statements(self, statements):
        self.env.push()
        for statement in statements:
            if self.trace_output:
                print(statement)
            status = ExecStatus.CONTINUE
            if statement.elem_type == InterpreterBase.FCALL_DEF:
                self.__call_func(statement)
            
            elif statement.elem_type == "=":
                self.__assign(statement)
            elif statement.elem_type == InterpreterBase.RETURN_DEF:
                status, return_val = self.__do_return(statement)
            elif statement.elem_type == Interpreter.IF_DEF:
                status, return_val = self.__do_if(statement)
            elif statement.elem_type == Interpreter.WHILE_DEF:
                status, return_val = self.__do_while(statement)
            
            elif statement.elem_type == Interpreter.MCALL_DEF:
                self.__do_mcall(statement)

            if status == ExecStatus.RETURN:
                self.env.pop()
                return (status, return_val)

        self.env.pop()
        return (ExecStatus.CONTINUE, Interpreter.NIL_VALUE)

    def __call_func(self, call_node):
        func_name = call_node.get("name")
        
        if func_name == "print":
            return self.__call_print(call_node)
        if func_name == "inputi":
            return self.__call_input(call_node)
        if func_name == "inputs":
            return self.__call_input(call_node)

        actual_args = call_node.get("args")
        obj_ref = call_node.get('objref')
        if obj_ref == "this":
            obj_ref = self.curr_obj
        
        func_flag = False
        obj_flag = False
        
        if self.env.get(func_name) is not None:
            func_flag = True
        #lambdas
        if func_flag and self.env.get(func_name).type() == Type.LAMBDA:
            func_ast = self.env.get(func_name).value().lambda_func
            
        #first class functions
        elif func_flag and self.env.get(func_name).type() == Type.FUNCTION:
            for index in self.env.get(func_name).value():
                func_ast = self.env.get(func_name).value()[index]
                break
        
        #object method call
        elif obj_ref is not None:
            obj_flag = True
            obj = self.env.get(obj_ref)
            if obj.t != Type.OBJECT:
                super().error(
                ErrorType.TYPE_ERROR,
                f"{obj_ref} is not an object!",
            )
            try:
                func_obj = obj.v.get_field(func_name)
            except:
                super().error(ErrorType.NAME_ERROR, f"{func_name} not a field of Object {obj_ref}")
            if func_obj.t == Type.LAMBDA:
                func_ast = func_obj.v.lambda_func
                
            elif func_obj.t == Type.FUNCTION:
                for index in func_obj.v:
                    func_ast = func_obj.v[index]
                    break
         
        #base case       
        elif func_flag:
            super().error(
                ErrorType.TYPE_ERROR,
                f"Invalid Function/Lambda call",
            )
        
        else:
            func_ast = self.__get_func_by_name(func_name, len(actual_args))
            
        formal_args = func_ast.get("args")
        if len(actual_args) != len(formal_args):
            if self.env.get(func_name): #not None when first class or lambda -- call TYPE ERROR
                super().error(
                    ErrorType.TYPE_ERROR,
                    f"Invalid args for functions",
                )
            super().error(
                ErrorType.NAME_ERROR,
                f"Function {func_ast.get('name')} with {len(actual_args)} args not found",
            )
        if func_flag and self.env.get(func_name).type() == Type.LAMBDA:
            self.env.environment.append(self.env.get(func_name).value().lambda_scope)
        elif obj_flag and self.env.get(obj_ref).value().get_field(func_name).type() == Type.LAMBDA:
            self.env.environment.append(self.env.get(obj_ref).value().get_field(func_name).value().lambda_scope)
        else:
            self.env.push()
        
        self.referenced_names.append({})
        for formal_ast, actual_ast in zip(formal_args, actual_args):
            if formal_ast.elem_type == Interpreter.REFARG_DEF:
                result = self.__eval_expr(actual_ast)
                self.referenced_names[-1][actual_ast.get('name')] = formal_ast.get('name')
            else:
                result = copy.deepcopy(self.__eval_expr(actual_ast))
            arg_name = formal_ast.get("name")
            self.env.create(arg_name, result)
        _, return_val = self.__run_statements(func_ast.get("statements"))
        
        for ref in self.referenced_names[-1]:
            if '.' in ref:
                obj_cand = ref[:ref.index(".")]
                obj_field = ref[ref.index(".")+1:]
                self.referenced_names[-1][ref] = self.env.get(obj_cand).v.get_field(obj_field)
            else:
                self.referenced_names[-1][ref] = self.env.get(self.referenced_names[-1][ref])
                
        self.env.pop()
        
        for ref in self.referenced_names[-1]:
            self.env.set(ref, self.referenced_names[-1][ref])
        self.referenced_names.pop()
        return return_val

    def __call_print(self, call_ast):
        output = ""
        for arg in call_ast.get("args"):
            result = self.__eval_expr(arg)  # result is a Value object
            output = output + get_printable(result)
        super().output(output)
        return Interpreter.NIL_VALUE

    def __call_input(self, call_ast):
        args = call_ast.get("args")
        if args is not None and len(args) == 1:
            result = self.__eval_expr(args[0])
            super().output(get_printable(result))
        elif args is not None and len(args) > 1:
            super().error(
                ErrorType.NAME_ERROR, "No inputi() function that takes > 1 parameter"
            )
        inp = super().get_input()
        if call_ast.get("name") == "inputi":
            return Value(Type.INT, int(inp))
        if call_ast.get("name") == "inputs":
            return Value(Type.STRING, inp)

    def __assign(self, assign_ast):
        var_name = assign_ast.get("name")
        if var_name == "this":
            var_name = self.curr_obj
        value_obj = self.__eval_expr(assign_ast.get("expression"))
        
        # handle class field assignment!!
        if self.env.get(var_name) is not None and self.env.get(var_name).t in [Type.OBJECT, Type.LAMBDA]:
            self.referenced_names.append({})
            self.referenced_names[-1][var_name] = var_name
        
        if '.' in var_name:
            obj_name = var_name[:var_name.index('.')]
            if obj_name == "this": 
                obj_name = self.curr_obj 
            obj_candidate = self.env.get(obj_name)
            if obj_candidate is None:
                super().error(
                ErrorType.NAME_ERROR,
                f"{obj_name} not defined!",
            )
            if obj_candidate.t == Type.OBJECT:
                field_name = var_name[var_name.index('.')+1:]
                if field_name == "proto" and value_obj.t not in [Type.OBJECT, Type.NIL]:
                    super().error(
                        ErrorType.TYPE_ERROR,
                        f"{obj_name} cannot be assigned proto of non-Object",
                    ) 
                (obj_candidate.v).set_field(field_name, value_obj)
                
            else:
                super().error(
                ErrorType.TYPE_ERROR,
                f"{obj_name} is not an object!",
            )
            
        else:
            self.env.set(var_name, value_obj)    

    def __eval_expr(self, expr_ast):
        # print("here expr")
        # print("type: " + str(expr_ast.elem_type))
        if expr_ast.elem_type == InterpreterBase.NIL_DEF:
            # print("getting as nil")
            return Interpreter.NIL_VALUE
        if expr_ast.elem_type == InterpreterBase.INT_DEF:
            return Value(Type.INT, expr_ast.get("val"))
        if expr_ast.elem_type == InterpreterBase.STRING_DEF:
            # print("getting as str")
            return Value(Type.STRING, expr_ast.get("val"))
        if expr_ast.elem_type == InterpreterBase.BOOL_DEF:
            return Value(Type.BOOL, expr_ast.get("val"))
        if expr_ast.elem_type == InterpreterBase.VAR_DEF:
            var_name = expr_ast.get("name")
            # handle variable assignment to function name
            if var_name in self.func_name_to_ast:
                if len(self.func_name_to_ast[var_name]) >= 2:  #check if assigned to overloaded func -- throw an error if so :(
                    super().error(ErrorType.NAME_ERROR, f"Attempted assignment to overloaded function")
                return Value(Type.FUNCTION, self.func_name_to_ast[var_name])
            
            if '.' in var_name:
                obj_name = var_name[:var_name.index('.')]
                if obj_name == "this":
                    obj_name = self.curr_obj
                field_name = var_name[var_name.index('.')+1:]
                obj = self.env.get(obj_name)
                if obj is None:
                    super().error(ErrorType.NAME_ERROR, f"Object {obj_name} not found")
                if obj.t != Type.OBJECT:
                    super().error(ErrorType.TYPE_ERROR, f"{obj_name} not an Object")
                try:
                    return (obj.v).get_field(field_name)
                except:
                    super().error(ErrorType.NAME_ERROR, f"{field_name} not a field of Object {obj_name}")
                
            val = self.env.get(var_name)
            if val is None:
                super().error(ErrorType.NAME_ERROR, f"Variable {var_name} not found")
            return val
        if expr_ast.elem_type == InterpreterBase.FCALL_DEF:
            return self.__call_func(expr_ast)
        if expr_ast.elem_type in Interpreter.BIN_OPS:
            return self.__eval_op(expr_ast)
        if expr_ast.elem_type == Interpreter.NEG_DEF:
            return self.__eval_unary(expr_ast, Type.INT, lambda x: -1 * x)
        if expr_ast.elem_type == Interpreter.NOT_DEF:
            return self.__eval_unary(expr_ast, Type.BOOL, lambda x: not x)
        if expr_ast.elem_type == Interpreter.LAMBDA_DEF:
            return self.__handle_lambda(expr_ast)
        if expr_ast.elem_type == Interpreter.OBJ_DEF:
            return self.__instantiate_obj()
        if expr_ast.elem_type == Interpreter.MCALL_DEF:
            return self.__do_mcall(expr_ast)

    def __eval_op(self, arith_ast):
        left_value_obj = self.__eval_expr(arith_ast.get("op1"))
        right_value_obj = self.__eval_expr(arith_ast.get("op2"))
            
        if arith_ast.elem_type in ['==', '!=', '||', '&&']:
            if left_value_obj.type() == Type.INT:
                left_value_obj = Value(Type.BOOL, bool(left_value_obj.value()))
            if right_value_obj.type() == Type.INT:
                right_value_obj = Value(Type.BOOL, bool(right_value_obj.value()))
                
        if arith_ast.elem_type in ['+', '-', '/', '*']:
            if left_value_obj.type() == Type.BOOL:
                left_value_obj = Value(Type.INT, int(left_value_obj.value()))
            if right_value_obj.type() == Type.BOOL:
                right_value_obj = Value(Type.INT, int(right_value_obj.value()))
                
        if not self.__compatible_types(
            arith_ast.elem_type, left_value_obj, right_value_obj
        ):
            super().error(
                ErrorType.TYPE_ERROR,
                f"Incompatible types for {arith_ast.elem_type} operation",
            )
                
        if arith_ast.elem_type not in self.op_to_lambda[left_value_obj.type()]:
            super().error(
                ErrorType.TYPE_ERROR,
                f"Incompatible operator {arith_ast.elem_type} for type {left_value_obj.type()}",
            )
                
        f = self.op_to_lambda[left_value_obj.type()][arith_ast.elem_type]
        # print("here eval")
        # print(arith_ast)
        # print("evaluating " + str(left_value_obj.type()) + " " + str(arith_ast.elem_type))
        # print("obj left: " + str(left_value_obj.value()))
        return f(left_value_obj, right_value_obj)

    def __compatible_types(self, oper, obj1, obj2):
        # DOCUMENT: allow comparisons ==/!= of anything against anything
        if oper in ["==", "!="]:
            return True
        return obj1.type() == obj2.type()

    def __eval_unary(self, arith_ast, t, f):
        value_obj = self.__eval_expr(arith_ast.get("op1"))
        if value_obj.type() != t and value_obj.type() != Type.INT:
            super().error(
                ErrorType.TYPE_ERROR,
                f"Incompatible type for {arith_ast.elem_type} operation",
            )
        return Value(t, f(value_obj.value()))

    def __setup_ops(self):
        self.op_to_lambda = {}
        # set up operations on integers
        self.op_to_lambda[Type.INT] = {}
        self.op_to_lambda[Type.INT]["+"] = lambda x, y: Value(
            x.type(), x.value() + y.value()
        )
        self.op_to_lambda[Type.INT]["-"] = lambda x, y: Value(
            x.type(), x.value() - y.value()
        )
        self.op_to_lambda[Type.INT]["*"] = lambda x, y: Value(
            x.type(), x.value() * y.value()
        )
        self.op_to_lambda[Type.INT]["/"] = lambda x, y: Value(
            x.type(), x.value() // y.value()
        )
        self.op_to_lambda[Type.INT]["=="] = lambda x, y: Value(
            Type.BOOL, x.type() == y.type() and x.value() == y.value()
        )
        self.op_to_lambda[Type.INT]["!="] = lambda x, y: Value(
            Type.BOOL, x.type() != y.type() or x.value() != y.value()
        )
        self.op_to_lambda[Type.INT]["<"] = lambda x, y: Value(
            Type.BOOL, x.value() < y.value()
        )
        self.op_to_lambda[Type.INT]["<="] = lambda x, y: Value(
            Type.BOOL, x.value() <= y.value()
        )
        self.op_to_lambda[Type.INT][">"] = lambda x, y: Value(
            Type.BOOL, x.value() > y.value()
        )
        self.op_to_lambda[Type.INT][">="] = lambda x, y: Value(
            Type.BOOL, x.value() >= y.value()
        )
        #  set up operations on strings
        self.op_to_lambda[Type.STRING] = {}
        self.op_to_lambda[Type.STRING]["+"] = lambda x, y: Value(
            x.type(), x.value() + y.value()
        )
        self.op_to_lambda[Type.STRING]["=="] = lambda x, y: Value(
            Type.BOOL, x.value() == y.value()
        )
        self.op_to_lambda[Type.STRING]["!="] = lambda x, y: Value(
            Type.BOOL, x.value() != y.value()
        )
        #  set up operations on bools
        self.op_to_lambda[Type.BOOL] = {}
        self.op_to_lambda[Type.BOOL]["&&"] = lambda x, y: Value(
            x.type(), x.value() and y.value()
        )
        self.op_to_lambda[Type.BOOL]["||"] = lambda x, y: Value(
            x.type(), x.value() or y.value()
        )
        self.op_to_lambda[Type.BOOL]["=="] = lambda x, y: Value(
            Type.BOOL, x.type() == y.type() and x.value() == y.value()
        )
        self.op_to_lambda[Type.BOOL]["!="] = lambda x, y: Value(
            Type.BOOL, x.type() != y.type() or x.value() != y.value()
        )

        #  set up operations on nil
        self.op_to_lambda[Type.NIL] = {}
        self.op_to_lambda[Type.NIL]["=="] = lambda x, y: Value(
            Type.BOOL, x.type() == y.type() and x.value() == y.value()
        )
        self.op_to_lambda[Type.NIL]["!="] = lambda x, y: Value(
            Type.BOOL, x.type() != y.type() or x.value() != y.value()
        )
        
        #setting up lambda
        self.op_to_lambda[Type.LAMBDA] = {}
        self.op_to_lambda[Type.LAMBDA]["=="] = lambda x, y: Value(
            Type.BOOL, x.type() == y.type() and x.value() == y.value()
        )
        self.op_to_lambda[Type.LAMBDA]["!="] = lambda x, y: Value(
            Type.BOOL, x.type() != y.type() or x.value() != y.value()
        )
        
        #setting up functions
        self.op_to_lambda[Type.FUNCTION] = {}
        self.op_to_lambda[Type.FUNCTION]["=="] = lambda x, y: Value(
            Type.BOOL, x.type() == y.type() and x.value() == y.value()
        )
        self.op_to_lambda[Type.FUNCTION]["!="] = lambda x, y: Value(
            Type.BOOL, x.type() != y.type() or x.value() != y.value()
        )
        
        self.op_to_lambda[Type.OBJECT] = {}
        self.op_to_lambda[Type.OBJECT]["=="] = lambda x, y: Value(
            Type.BOOL, x.type() == y.type() and x.value() == y.value()
        )
        self.op_to_lambda[Type.OBJECT]["!="] = lambda x, y: Value(
            Type.BOOL, x.type() != y.type() or x.value() != y.value()
        )
        
    def __do_if(self, if_ast):
        cond_ast = if_ast.get("condition")
        result = self.__eval_expr(cond_ast)
        if result.type() != Type.BOOL and result.type() != Type.INT:
            super().error(
                ErrorType.TYPE_ERROR,
                "Incompatible type for if condition",
            )
        if result.value():
            statements = if_ast.get("statements")
            status, return_val = self.__run_statements(statements)
            return (status, return_val)
        else:
            else_statements = if_ast.get("else_statements")
            if else_statements is not None:
                status, return_val = self.__run_statements(else_statements)
                return (status, return_val)

        return (ExecStatus.CONTINUE, Interpreter.NIL_VALUE)

    def __do_while(self, while_ast):
        cond_ast = while_ast.get("condition")
        run_while = Interpreter.TRUE_VALUE
        while run_while.value():
            run_while = self.__eval_expr(cond_ast)
            if run_while.type() != Type.BOOL and run_while.type() != Type.INT:
                super().error(
                    ErrorType.TYPE_ERROR,
                    "Incompatible type for while condition",
                )
            if run_while.value():
                statements = while_ast.get("statements")
                status, return_val = self.__run_statements(statements)
                if status == ExecStatus.RETURN:
                    return status, return_val

        return (ExecStatus.CONTINUE, Interpreter.NIL_VALUE)

    def __do_return(self, return_ast):
        expr_ast = return_ast.get("expression")
        if expr_ast is None:
            return (ExecStatus.RETURN, Interpreter.NIL_VALUE)
        value_obj = copy.deepcopy(self.__eval_expr(expr_ast))
        return (ExecStatus.RETURN, value_obj)
    
    def __handle_lambda(self, lambda_ast):
        lambda_env = {}
        env_copy = copy.deepcopy(self.env).environment
        for item in reversed(env_copy):
            for elem in item:
                lambda_env[elem] = self.env.get(elem) 
        return Value(Type.LAMBDA, Lambda(lambda_ast, lambda_env))
    
    def __instantiate_obj(self):
        return Value(Type.OBJECT, Object())
    
    def __do_mcall(self, mcall_ast):
        obj_name = mcall_ast.get('objref')
        if obj_name == "this":
            obj_name = self.curr_obj
        obj = self.env.get(obj_name)
        if obj is None:
            super().error(ErrorType.NAME_ERROR, f"Object {obj_name} not found")
        if obj.t != Type.OBJECT:
            super().error(ErrorType.TYPE_ERROR, f"{obj_name} not an Object")
        func_name = mcall_ast.get('name')
        try:
            method = obj.v.get_field(func_name)
        except:
            super().error(ErrorType.NAME_ERROR, f"{func_name} not a field of Object {obj_name}")
        if method.t not in [Type.LAMBDA, Type.FUNCTION]:
            super().error(ErrorType.TYPE_ERROR, f"{func_name} not a method")
        self.curr_obj = obj_name
        return self.__call_func(mcall_ast)
        

        
         
def main():
    interpreter = Interpreter()
    program = """
   func main() {
        p1 = @;
        p2 = @;
        p3 = @;
        p1.proto = p2;
        p2.proto = p3;
        p3.foo = lambda() {print("hi");};
        p1.foo();
}
    """

    interpreter.run(program)

if __name__ == '__main__':
    main()
