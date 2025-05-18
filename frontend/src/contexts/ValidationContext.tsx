import React, { createContext, useContext, useState, useCallback } from 'react';

type ValidationRule = (value: any) => string | null;

interface ValidationRules {
  [key: string]: ValidationRule[];
}

interface ValidationContextType {
  rules: ValidationRules;
  addRule: (field: string, rule: ValidationRule) => void;
  removeRule: (field: string, rule: ValidationRule) => void;
  validateField: (field: string, value: any) => string | null;
  validateForm: (values: Record<string, any>) => Record<string, string | null>;
}

const ValidationContext = createContext<ValidationContextType | undefined>(undefined);

export const ValidationProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [rules, setRules] = useState<ValidationRules>({});

  const addRule = useCallback((field: string, rule: ValidationRule) => {
    setRules((prev) => ({
      ...prev,
      [field]: [...(prev[field] || []), rule],
    }));
  }, []);

  const removeRule = useCallback((field: string, rule: ValidationRule) => {
    setRules((prev) => ({
      ...prev,
      [field]: (prev[field] || []).filter((r) => r !== rule),
    }));
  }, []);

  const validateField = useCallback(
    (field: string, value: any): string | null => {
      const fieldRules = rules[field] || [];
      for (const rule of fieldRules) {
        const error = rule(value);
        if (error) return error;
      }
      return null;
    },
    [rules]
  );

  const validateForm = useCallback(
    (values: Record<string, any>): Record<string, string | null> => {
      const errors: Record<string, string | null> = {};
      Object.keys(rules).forEach((field) => {
        errors[field] = validateField(field, values[field]);
      });
      return errors;
    },
    [rules, validateField]
  );

  return (
    <ValidationContext.Provider
      value={{
        rules,
        addRule,
        removeRule,
        validateField,
        validateForm,
      }}
    >
      {children}
    </ValidationContext.Provider>
  );
};

export const useValidation = () => {
  const context = useContext(ValidationContext);
  if (context === undefined) {
    throw new Error('useValidation must be used within a ValidationProvider');
  }
  return context;
};
