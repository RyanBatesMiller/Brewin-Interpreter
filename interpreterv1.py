from brewparse import parse_program
from intbase import InterpreterBase
from intbase import ErrorType

class Interpreter(InterpreterBase):
    def __init__(self, console_output=True, inp=None, trace_output=False):
        super().__init__(console_output, inp)   # call InterpreterBase's constructor

    
    def run(self, program):
        self.ast = parse_program(program)
        self.variable_map = {}
        main_func_node = (self.ast.get('functions'))[0] 
        
        if main_func_node.get('name') != 'main':
            super().error(
                ErrorType.NAME_ERROR,
                 "No main() function was found",
            )

        self.run_func(main_func_node)                                


    def run_func(self, func_node):                  # function handling :(
	    for statement in func_node.get('statements'):
		    self.run_statement(statement)
        
          
    def run_statement(self, statement_node):        # statement handling :|
        
        statement_type = statement_node.elem_type
        statement_name = statement_node.get('name')
        
        if statement_type == "=":                 
            self.do_assignment(statement_node)
        elif statement_type == 'fcall':              
            if statement_name == "print":
                self.do_print(statement_node)
            elif statement_name == "inputi":
                self.do_inputi(statement_node)
            else:
                super().error(
                ErrorType.NAME_ERROR,
                f"{statement_node.get('name')} function undefined",
                )
        else:
            self.evaluate_expression(statement_node)
        return

    def do_assignment(self, statement_node):         # assignment handling :)
        var_name = statement_node.get('name')
        expression = statement_node.get('expression')
        var_info = self.evaluate_expression(expression) 
        self.variable_map[var_name] = var_info    #[value, type] 
     
    def evaluate_expression(self, expression_node):  # expression evaluation ;) -> return list [value, value type]
        
        expression_node_type = expression_node.elem_type
        
        if expression_node_type == "+" or expression_node_type == "-":
            
            op1 = expression_node.get('op1') 
            op2 = expression_node.get('op2')
            
            # ops can be values (int or string), expressions, or var
            value1_info = self.evaluate_expression(op1)
            value2_info = self.evaluate_expression(op2)
            
            value1 = value1_info[0]
            value2 = value2_info[0]
            
            type1 = value1_info[1]
            type2 = value2_info[1]
            
            if type1 != type2:
                super().error(
                    ErrorType.TYPE_ERROR,
                    "Incompatible types for arithmetic operation",
                )
               

            match expression_node_type:
                case "+":
                    return [value1 + value2, type1]
                case "-":
                    return [value1 - value2, type2]
                
                
        if expression_node_type == "var":
            var_name = expression_node.get('name')
            if var_name not in self.variable_map:
                super().error(
                    ErrorType.NAME_ERROR,
                    f"Variable {var_name} has not been defined",
                )
                

            return self.variable_map[var_name]
        
        
        if expression_node_type == "neg":
            val_info = self.evaluate_expression(expression_node.get('op1'))
            value = val_info[0]
            type = val_info[1]
            
            if type != "int":
                super().error(
                    ErrorType.TYPE_ERROR,
                    "Incompatible types for negation operation",
                )
            return [-1*value, "int"]
            
        if expression_node_type == "int" or expression_node_type == "string":
            return [expression_node.get('val'), expression_node_type]
        
        
        if expression_node_type == "fcall":
            
            func_name = expression_node.get('name')
            
            if func_name == "print":
                self.do_print(expression_node)
                
            elif func_name == "inputi":
                return self.do_inputi(expression_node)
                
            else:
                super().error(
                    ErrorType.NAME_ERROR,
                    f"{func_name} function undefined",
            )
        
        else:
            super().error(
                    ErrorType.NAME_ERROR,
                    f"{expression_node.get('name')} undefined",
            )
                
        
        
    def do_print(self, print_expression):
        print_args = print_expression.get('args')
        output = ""
        for arg in print_args:
            output += str(self.evaluate_expression(arg)[0])
            
        super().output(output)
            
            
    def do_inputi(self, inputi_expression):
        inputi_args = inputi_expression.get('args')
        num_args = len(inputi_args)
        if num_args > 1:
            super().error(
                ErrorType.NAME_ERROR,
                f"No inputi() function found that takes > 1 parameter",
            )
        
        elif num_args == 1:
            arg_type = inputi_args[0].elem_type
            match arg_type:
                case "string" | "int":
                    super().output(str(inputi_args[0].get('val')))
                case "neg" | "+" | "-" | "fcall":
                    if inputi_args[0].get('name') == "print":
                        super().error(
                            ErrorType.NAME_ERROR,
                            f"Invalid inputi() parameter",
                        )
                    super().output(str((self.evaluate_expression(inputi_args[0]))[0]))
                case "var":
                    super().output(str(self.variable_map[inputi_args[0].get('name')][0]))
                case _:
                    super().error(
                        ErrorType.NAME_ERROR,
                        f"Invalid inputi() parameter",
                    )
                    

        return [int(super().get_input()), "int"]
        
        
         
def main():
    interpreter = Interpreter(trace_output=True)
    program = """func main() {
    name = "Ryan";
    print(name, " is ", inputi("Enter your age: ") + 5, " years old!");
    }
    """

    interpreter.run(program)

if __name__ == '__main__':
    main()

