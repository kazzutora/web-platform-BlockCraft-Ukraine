import { z } from "zod";

import { authCopy } from "./copy";

const { errors } = authCopy;

const email = z.email({ error: errors.email });
const password = z.string().min(8, { error: errors.passwordShort });

/** Mirrors the backend rules for nicknames (apps/accounts/validators.py). */
export const nicknameSchema = z
  .string()
  .min(3, { error: errors.nicknameLength })
  .max(24, { error: errors.nicknameLength })
  .regex(/^[a-zA-Z0-9_]+$/, { error: errors.nicknameFormat });

export const loginSchema = z.object({
  email,
  password: z.string().min(1, { error: errors.required }),
});

export const registerSchema = z.object({ email, username: nicknameSchema, password });

export const resetRequestSchema = z.object({ email });

export const resetPasswordSchema = z.object({ password });

export const providerSignupSchema = z.object({ email, username: nicknameSchema });

export const changePasswordSchema = z.object({
  current_password: z.string().min(1, { error: errors.required }),
  new_password: password,
});

export type LoginValues = z.infer<typeof loginSchema>;
export type RegisterValues = z.infer<typeof registerSchema>;
export type ResetRequestValues = z.infer<typeof resetRequestSchema>;
export type ResetPasswordValues = z.infer<typeof resetPasswordSchema>;
export type ProviderSignupValues = z.infer<typeof providerSignupSchema>;
export type ChangePasswordValues = z.infer<typeof changePasswordSchema>;
