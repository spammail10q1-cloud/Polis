export type FormErrors<T extends string = string> = Partial<Record<T, string>>;

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export function validateEmail(email: string): string | null {
  if (!email.trim()) return "Email is required.";
  if (!EMAIL_RE.test(email.trim())) return "Enter a valid email address.";
  return null;
}

export function validateLogin(input: { email: string; password: string }): FormErrors<"email" | "password"> {
  const errors: FormErrors<"email" | "password"> = {};
  const email = validateEmail(input.email);
  if (email) errors.email = email;
  if (!input.password) errors.password = "Password is required.";
  return errors;
}

export function validateRegister(input: {
  name: string;
  email: string;
  password: string;
  accept_terms: boolean;
}): FormErrors<"name" | "email" | "password" | "accept_terms"> {
  const errors: FormErrors<"name" | "email" | "password" | "accept_terms"> = {};
  if (input.name.trim().length < 2) errors.name = "Enter your name.";
  const email = validateEmail(input.email);
  if (email) errors.email = email;
  if (input.password.length < 10) errors.password = "Use at least 10 characters.";
  else if (!/[A-Za-z]/.test(input.password) || !/\d/.test(input.password)) {
    errors.password = "Include at least one letter and one number.";
  }
  if (!input.accept_terms) errors.accept_terms = "Accept the terms and privacy notice to continue.";
  return errors;
}
