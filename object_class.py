class Object():
    def __init__(self):
        self.dict = {}
        self.inherited = []
    
    def set_field(self, field_or_method_name, val):
        if field_or_method_name == "proto":
            if val.v is None:
                temp = {}
                for field in self.dict:
                    if field not in self.inherited:
                        temp[field] = self.dict[field]
                self.dict = temp
                self.inherited = []
            else:
                new_inherited = []
                for field in self.inherited:
                    self.dict.pop(field)
                for field in val.v.dict:
                    # only change if object did not originally defined field OR object inherited field
                    if field not in self.dict or field in self.inherited:
                        self.dict[field] = val.v.dict[field]
                        new_inherited.append(field)
                self.inherited = new_inherited
                      
        self.dict[field_or_method_name] = val
        
    def get_field(self, field_or_method_name):
        if field_or_method_name in self.dict:
            return self.dict[field_or_method_name]
        return self.dict["proto"].v.get_field(field_or_method_name)
    
    
    
        
        
    