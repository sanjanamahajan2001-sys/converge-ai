import React, { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '@/lib/auth/AuthContext';
import { ApiClientError } from '@/lib/api/client';
import { Card } from '@/components/ui/Card';

export const Register: React.FC = () => {
  const { register } = useAuth();
  const navigate = useNavigate();

  const [formData, setFormData] = useState({
    username: '',
    email: '',
    password: '',
    confirmPassword: '',
    fullName: '',
    companyName: '',
    jobTitle: '',
    phoneNumber: '',
  });

  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const [generalError, setGeneralError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [registrationSuccess, setRegistrationSuccess] = useState(false);

  // Auto-redirect to login after successful account creation
  useEffect(() => {
    if (registrationSuccess) {
      const timer = setTimeout(() => {
        navigate('/login', {
          replace: true,
          state: {
            registeredUsername: formData.username.trim(),
            successMessage: 'Account created successfully! Please sign in with your credentials.',
          },
        });
      }, 2500);
      return () => clearTimeout(timer);
    }
  }, [registrationSuccess, formData.username, navigate]);

  const validate = (): boolean => {
    const errors: Record<string, string> = {};

    // Full Name
    if (!formData.fullName.trim()) {
      errors.fullName = 'Full name is required.';
    }

    // Username validation
    const trimmedUsername = formData.username.trim();
    if (!trimmedUsername) {
      errors.username = 'Username is required.';
    } else if (trimmedUsername.includes('@') || trimmedUsername.includes('.')) {
      errors.username = 'Username cannot be an email address. Choose a handle using letters, numbers, underscores, or hyphens (e.g. sanjana_m).';
    } else if (trimmedUsername.length < 3 || trimmedUsername.length > 50) {
      errors.username = 'Username must be between 3 and 50 characters.';
    } else if (!/^[a-zA-Z0-9_-]+$/.test(trimmedUsername)) {
      errors.username = 'Username may only contain letters, numbers, underscores, and hyphens.';
    }

    // Email validation
    const trimmedEmail = formData.email.trim();
    const emailRegex = /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/;
    if (!trimmedEmail) {
      errors.email = 'Email address is required.';
    } else if (!emailRegex.test(trimmedEmail)) {
      errors.email = 'Please provide a valid email address (e.g. name@example.com).';
    }

    // Indian Phone Number validation (Optional)
    const rawPhone = formData.phoneNumber.trim();
    if (rawPhone) {
      const cleanPhone = rawPhone.replace(/[\s\-()]/g, '');
      const indianPhoneRegex = /^(?:\+91|91|0)?[6-9]\d{9}$/;
      if (!indianPhoneRegex.test(cleanPhone)) {
        errors.phoneNumber = 'Please enter a valid 10-digit Indian mobile number (e.g. +91 98765 43210).';
      }
    }

    // Password validation (Aligned to backend minimum: 10 chars + complexity)
    if (!formData.password) {
      errors.password = 'Password is required.';
    } else {
      if (formData.password.length < 10) {
        errors.password = 'Password must be at least 10 characters long.';
      } else if (!/[A-Z]/.test(formData.password)) {
        errors.password = 'Password must include at least one uppercase letter.';
      } else if (!/[a-z]/.test(formData.password)) {
        errors.password = 'Password must include at least one lowercase letter.';
      } else if (!/[0-9]/.test(formData.password)) {
        errors.password = 'Password must include at least one number.';
      } else if (!/[!@#$%^&*(),.?":{}|<>_\+\-=\[\]\\/;`~]/.test(formData.password)) {
        errors.password = 'Password must include at least one special character.';
      }
    }

    // Password confirmation
    if (formData.password !== formData.confirmPassword) {
      errors.confirmPassword = 'Passwords do not match.';
    }

    setFieldErrors(errors);

    // If validation failed, surface top-level alert and focus the first invalid field
    if (Object.keys(errors).length > 0) {
      setGeneralError('Please correct the highlighted errors before submitting.');
      const firstField = Object.keys(errors)[0];
      const el = document.getElementById(firstField);
      if (el) {
        el.focus();
        if (typeof el.scrollIntoView === 'function') {
          el.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }
      }
      return false;
    }

    return true;
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
    if (fieldErrors[name]) {
      setFieldErrors((prev) => {
        const updated = { ...prev };
        delete updated[name];
        return updated;
      });
    }
    setGeneralError(null);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!validate() || isSubmitting) return;

    setIsSubmitting(true);
    setGeneralError(null);

    // Format phone number cleanly to Indian standard +91 XXXXX XXXXX if present
    let formattedPhone: string | null = null;
    const rawPhone = formData.phoneNumber.trim();
    if (rawPhone) {
      const cleanPhone = rawPhone.replace(/[\s\-()]/g, '');
      const digits = cleanPhone.slice(-10);
      formattedPhone = `+91 ${digits.slice(0, 5)} ${digits.slice(5)}`;
    }

    try {
      await register({
        username: formData.username.trim(),
        email: formData.email.trim().toLowerCase(),
        password: formData.password,
        full_name: formData.fullName.trim(),
        company_name: formData.companyName.trim() || null,
        job_title: formData.jobTitle.trim() || null,
        phone_number: formattedPhone,
      });

      setRegistrationSuccess(true);
    } catch (err) {
      if (err instanceof ApiClientError) {
        if (err.status === 409) {
          if (err.detail.toLowerCase().includes('username')) {
            setFieldErrors((prev) => ({ ...prev, username: err.detail }));
          } else if (err.detail.toLowerCase().includes('email')) {
            setFieldErrors((prev) => ({ ...prev, email: err.detail }));
          } else {
            setGeneralError(err.detail);
          }
        } else if (err.status === 422) {
          setGeneralError(err.detail || 'Validation error. Please verify your submission.');
        } else {
          setGeneralError(err.detail || 'Registration failed. Please try again.');
        }
      } else {
        setGeneralError('Network failure. Please verify your connection.');
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  if (registrationSuccess) {
    return (
      <div className="w-full max-w-xl mx-auto py-10 sm:py-16 px-4">
        <Card title="Registration Complete" subtitle="Account Created">
          <div className="text-center py-6 space-y-4">
            <div className="text-5xl select-none" aria-hidden="true">🎉</div>
            <div className="space-y-1">
              <h2 className="text-lg font-serif font-bold text-ink-primary">
                Account Created Successfully!
              </h2>
              <p className="text-sm text-ink-secondary">
                Welcome to Converge AI, <strong className="text-ink-primary font-semibold">@{formData.username.trim()}</strong>.
              </p>
            </div>
            <p className="text-xs text-ink-muted max-w-md mx-auto">
              Redirecting you to the sign-in page in a moment, or click below to proceed immediately.
            </p>
            <div className="pt-3 max-w-sm mx-auto">
              <button
                type="button"
                onClick={() =>
                  navigate('/login', {
                    replace: true,
                    state: {
                      registeredUsername: formData.username.trim(),
                      successMessage: 'Account created successfully! Please sign in with your credentials.',
                    },
                  })
                }
                className="w-full inline-flex justify-center items-center gap-2 px-4 py-2.5 text-sm font-semibold rounded-md text-white bg-brass hover:bg-brass/90 transition-colors shadow-sm"
              >
                <span>Proceed to Log In</span>
                <span aria-hidden="true">→</span>
              </button>
            </div>
          </div>
        </Card>
      </div>
    );
  }

  return (
    <div className="w-full max-w-2xl lg:max-w-3xl mx-auto py-8 sm:py-12 px-4 sm:px-6">
      <div className="text-center mb-8">
        <div className="inline-flex items-center justify-center w-12 h-12 rounded-lg bg-canvas-elevated border border-canvas-border text-2xl mb-3 shadow-xs">
          ✍️
        </div>
        <h1 className="font-serif text-2xl sm:text-3xl font-bold text-ink-primary tracking-tight">
          Conference Participant Registration
        </h1>
        <p className="text-xs sm:text-sm text-ink-secondary mt-1 max-w-lg mx-auto">
          Create your participant account to enable background agent networking and coffee chat scheduling.
        </p>
      </div>

      <Card title="Participant Details" subtitle="Required credentials and contact information">
        <form onSubmit={handleSubmit} noValidate className="space-y-5">
          {generalError && (
            <div
              className="p-3.5 bg-crimson-light/50 border border-crimson/30 rounded-md text-xs sm:text-sm text-crimson font-medium flex items-center gap-2.5"
              role="alert"
            >
              <span aria-hidden="true" className="text-base select-none">⚠️</span>
              <span>{generalError}</span>
            </div>
          )}

          {/* Row 1: Full Name & Username */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label htmlFor="fullName" className="block text-xs font-semibold text-ink-primary mb-1">
                Full Name <span className="text-crimson">*</span>
              </label>
              <input
                id="fullName"
                name="fullName"
                type="text"
                autoComplete="name"
                required
                value={formData.fullName}
                onChange={handleChange}
                className={`w-full px-3 py-2 text-sm bg-canvas-base border rounded-md text-ink-primary placeholder:text-ink-muted focus:outline-none focus:ring-2 focus:ring-brass/30 focus:border-brass transition-colors ${
                  fieldErrors.fullName ? 'border-crimson focus:border-crimson focus:ring-crimson/20' : 'border-canvas-border'
                }`}
                placeholder="e.g. Sanjana Sharma"
              />
              {fieldErrors.fullName && (
                <p className="mt-1 text-xs text-crimson font-medium">{fieldErrors.fullName}</p>
              )}
            </div>

            <div>
              <label htmlFor="username" className="block text-xs font-semibold text-ink-primary mb-1">
                Username <span className="text-crimson">*</span>
              </label>
              <input
                id="username"
                name="username"
                type="text"
                autoComplete="username"
                required
                value={formData.username}
                onChange={handleChange}
                className={`w-full px-3 py-2 text-sm bg-canvas-base border rounded-md text-ink-primary placeholder:text-ink-muted focus:outline-none focus:ring-2 focus:ring-brass/30 focus:border-brass transition-colors ${
                  fieldErrors.username ? 'border-crimson focus:border-crimson focus:ring-crimson/20' : 'border-canvas-border'
                }`}
                placeholder="e.g. sanjana_dev"
              />
              {fieldErrors.username ? (
                <p className="mt-1 text-xs text-crimson font-medium">{fieldErrors.username}</p>
              ) : (
                <p className="mt-1 text-[11px] text-ink-muted">
                  Letters, numbers, underscores, or hyphens. Not an email.
                </p>
              )}
            </div>
          </div>

          {/* Row 2: Email & Phone Number */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label htmlFor="email" className="block text-xs font-semibold text-ink-primary mb-1">
                Email Address <span className="text-crimson">*</span>
              </label>
              <input
                id="email"
                name="email"
                type="email"
                autoComplete="email"
                required
                value={formData.email}
                onChange={handleChange}
                className={`w-full px-3 py-2 text-sm bg-canvas-base border rounded-md text-ink-primary placeholder:text-ink-muted focus:outline-none focus:ring-2 focus:ring-brass/30 focus:border-brass transition-colors ${
                  fieldErrors.email ? 'border-crimson focus:border-crimson focus:ring-crimson/20' : 'border-canvas-border'
                }`}
                placeholder="e.g. sanjana@example.com"
              />
              {fieldErrors.email && (
                <p className="mt-1 text-xs text-crimson font-medium">{fieldErrors.email}</p>
              )}
            </div>

            <div>
              <label htmlFor="phoneNumber" className="block text-xs font-semibold text-ink-primary mb-1">
                Phone Number <span className="text-ink-muted font-normal">(Optional — +91 India)</span>
              </label>
              <input
                id="phoneNumber"
                name="phoneNumber"
                type="tel"
                autoComplete="tel"
                value={formData.phoneNumber}
                onChange={handleChange}
                className={`w-full px-3 py-2 text-sm bg-canvas-base border rounded-md text-ink-primary placeholder:text-ink-muted focus:outline-none focus:ring-2 focus:ring-brass/30 focus:border-brass transition-colors ${
                  fieldErrors.phoneNumber ? 'border-crimson focus:border-crimson focus:ring-crimson/20' : 'border-canvas-border'
                }`}
                placeholder="+91 98765 43210"
              />
              {fieldErrors.phoneNumber ? (
                <p className="mt-1 text-xs text-crimson font-medium">{fieldErrors.phoneNumber}</p>
              ) : (
                <p className="mt-1 text-[11px] text-ink-muted">
                  Valid 10-digit Indian mobile number (e.g. +91 98765 43210).
                </p>
              )}
            </div>
          </div>

          {/* Row 3: Company & Job Title */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label htmlFor="companyName" className="block text-xs font-semibold text-ink-primary mb-1">
                Company / Organization <span className="text-ink-muted font-normal">(Optional)</span>
              </label>
              <input
                id="companyName"
                name="companyName"
                type="text"
                autoComplete="organization"
                value={formData.companyName}
                onChange={handleChange}
                className="w-full px-3 py-2 text-sm bg-canvas-base border border-canvas-border rounded-md text-ink-primary placeholder:text-ink-muted focus:outline-none focus:ring-2 focus:ring-brass/30 focus:border-brass transition-colors"
                placeholder="e.g. Converge AI Labs"
              />
            </div>

            <div>
              <label htmlFor="jobTitle" className="block text-xs font-semibold text-ink-primary mb-1">
                Job Title <span className="text-ink-muted font-normal">(Optional)</span>
              </label>
              <input
                id="jobTitle"
                name="jobTitle"
                type="text"
                autoComplete="organization-title"
                value={formData.jobTitle}
                onChange={handleChange}
                className="w-full px-3 py-2 text-sm bg-canvas-base border border-canvas-border rounded-md text-ink-primary placeholder:text-ink-muted focus:outline-none focus:ring-2 focus:ring-brass/30 focus:border-brass transition-colors"
                placeholder="e.g. Software Engineer"
              />
            </div>
          </div>

          {/* Row 4: Password & Confirm Password */}
          <div className="border-t border-canvas-border pt-4">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label htmlFor="password" className="block text-xs font-semibold text-ink-primary mb-1">
                  Password <span className="text-crimson">*</span>
                </label>
                <input
                  id="password"
                  name="password"
                  type="password"
                  autoComplete="new-password"
                  required
                  value={formData.password}
                  onChange={handleChange}
                  className={`w-full px-3 py-2 text-sm bg-canvas-base border rounded-md text-ink-primary placeholder:text-ink-muted focus:outline-none focus:ring-2 focus:ring-brass/30 focus:border-brass transition-colors ${
                    fieldErrors.password ? 'border-crimson focus:border-crimson focus:ring-crimson/20' : 'border-canvas-border'
                  }`}
                  placeholder="••••••••••••"
                />
                {fieldErrors.password && (
                  <p className="mt-1 text-xs text-crimson font-medium">{fieldErrors.password}</p>
                )}
              </div>

              <div>
                <label htmlFor="confirmPassword" className="block text-xs font-semibold text-ink-primary mb-1">
                  Confirm Password <span className="text-crimson">*</span>
                </label>
                <input
                  id="confirmPassword"
                  name="confirmPassword"
                  type="password"
                  autoComplete="new-password"
                  required
                  value={formData.confirmPassword}
                  onChange={handleChange}
                  className={`w-full px-3 py-2 text-sm bg-canvas-base border rounded-md text-ink-primary placeholder:text-ink-muted focus:outline-none focus:ring-2 focus:ring-brass/30 focus:border-brass transition-colors ${
                    fieldErrors.confirmPassword ? 'border-crimson focus:border-crimson focus:ring-crimson/20' : 'border-canvas-border'
                  }`}
                  placeholder="••••••••••••"
                />
                {fieldErrors.confirmPassword && (
                  <p className="mt-1 text-xs text-crimson font-medium">{fieldErrors.confirmPassword}</p>
                )}
              </div>
            </div>

            {/* Password requirements helper box */}
            <div className="mt-3 p-3 bg-canvas-elevated rounded-md border border-canvas-border text-[11px] text-ink-muted space-y-1.5">
              <p className="font-semibold text-ink-secondary">Password Security Requirements:</p>
              <ul className="grid grid-cols-1 sm:grid-cols-2 gap-1 font-mono text-[10px]">
                <li className="flex items-center gap-1.5">
                  <span aria-hidden="true">•</span> At least 10 characters in length
                </li>
                <li className="flex items-center gap-1.5">
                  <span aria-hidden="true">•</span> Uppercase and lowercase letters
                </li>
                <li className="flex items-center gap-1.5">
                  <span aria-hidden="true">•</span> At least one numeric digit (0-9)
                </li>
                <li className="flex items-center gap-1.5">
                  <span aria-hidden="true">•</span> At least one special symbol (!@#$...)
                </li>
              </ul>
            </div>
          </div>

          {/* Submission Action */}
          <div className="pt-2">
            <button
              type="submit"
              disabled={isSubmitting}
              className="w-full inline-flex justify-center items-center gap-2 px-4 py-2.5 text-sm font-semibold rounded-md text-white bg-brass hover:bg-brass/90 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-brass disabled:opacity-50 disabled:cursor-not-allowed transition-all shadow-sm"
            >
              {isSubmitting ? (
                <>
                  <span className="animate-spin" aria-hidden="true">⏳</span>
                  <span>Creating Account...</span>
                </>
              ) : (
                <>
                  <span>Create Account</span>
                  <span aria-hidden="true">→</span>
                </>
              )}
            </button>
          </div>

          <div className="text-center text-xs text-ink-muted pt-2 border-t border-canvas-border">
            Already have an account?{' '}
            <Link to="/login" className="text-brass hover:underline font-semibold">
              Log in here
            </Link>
          </div>
        </form>
      </Card>
    </div>
  );
};
