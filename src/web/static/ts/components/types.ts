/**
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

/**
 * Component Types and Interfaces
 * Complete TypeScript type definitions for all UI components
 */

// ============================================================================
// Common Base Props
// ============================================================================

export interface BaseComponentProps {
  className?: string;
  id?: string;
  ariaLabel?: string;
  onClick?: (event: MouseEvent) => void;
}

// ============================================================================
// Button Component
// ============================================================================

export interface ButtonProps extends BaseComponentProps {
  variant?: 'primary' | 'secondary' | 'accent' | 'ghost' | 'danger';
  size?: 'sm' | 'md' | 'lg';
  disabled?: boolean;
  loading?: boolean;
  title?: string;
  type?: 'button' | 'submit' | 'reset';
  icon?: string;
  iconPosition?: 'left' | 'right';
  fullWidth?: boolean;
}

// ============================================================================
// Card Component
// ============================================================================

export interface CardProps extends BaseComponentProps {
  variant?: 'default' | 'bordered' | 'elevated' | 'colored';
  padding?: 'compact' | 'default' | 'generous';
  clickable?: boolean;
  backgroundColor?: string;
  title?: string;
  description?: string;
  footer?: HTMLElement | string;
}

// ============================================================================
// Input Components
// ============================================================================

export interface InputProps extends BaseComponentProps {
  type?: string;
  placeholder?: string;
  value?: string;
  name?: string;
  error?: boolean;
  errorMessage?: string;
  success?: boolean;
  required?: boolean;
  disabled?: boolean;
  readonly?: boolean;
  maxLength?: number;
  minLength?: number;
  pattern?: string;
  helpText?: string;
  autocomplete?: string;
  onChange?: (event: Event) => void;
  onBlur?: (event: Event) => void;
  onFocus?: (event: Event) => void;
  onInput?: (event: Event) => void;
}

export interface TextareaProps extends Omit<InputProps, 'type'> {
  rows?: number;
  cols?: number;
}

export interface SelectProps extends BaseComponentProps {
  options: Array<{ value: string; label: string; disabled?: boolean }>;
  value?: string;
  name?: string;
  disabled?: boolean;
  required?: boolean;
  error?: boolean;
  errorMessage?: string;
  onChange?: (event: Event) => void;
}

export interface CheckboxProps extends BaseComponentProps {
  label: string;
  checked?: boolean;
  disabled?: boolean;
  required?: boolean;
  name?: string;
  value?: string;
  onChange?: (event: Event) => void;
}

export interface RadioOption {
  label: string;
  value: string;
  disabled?: boolean;
}

export interface RadioGroupProps extends BaseComponentProps {
  name: string;
  options: RadioOption[];
  value?: string;
  disabled?: boolean;
  required?: boolean;
  onChange?: (event: Event) => void;
}

export interface FileUploadProps extends BaseComponentProps {
  accept?: string;
  multiple?: boolean;
  disabled?: boolean;
  required?: boolean;
  name?: string;
  onChange?: (event: Event) => void;
  onFilesSelected?: (files: FileList | null) => void;
}

// ============================================================================
// Form Group Component
// ============================================================================

export interface FormGroupProps extends BaseComponentProps {
  label: string;
  required?: boolean;
  error?: string;
  helpText?: string;
  htmlFor?: string;
}

// ============================================================================
// Modal Component
// ============================================================================

export interface ModalAction {
  label: string;
  variant?: 'primary' | 'secondary' | 'danger';
  onClick: () => void;
}

export interface ModalProps extends BaseComponentProps {
  title: string;
  content: string | HTMLElement;
  actions?: ModalAction[];
  size?: 'sm' | 'md' | 'lg' | 'xl' | 'full';
  closable?: boolean;
  closeOnBackdrop?: boolean;
  closeOnEscape?: boolean;
  showClose?: boolean;
  onClose?: () => void;
}

// ============================================================================
// Layout Components
// ============================================================================

export interface ContainerProps extends BaseComponentProps {
  maxWidth?: 'sm' | 'md' | 'lg' | 'xl' | '2xl' | 'full';
  padding?: boolean;
}

export interface FlexProps extends BaseComponentProps {
  direction?: 'row' | 'col';
  gap?: 'xs' | 'sm' | 'md' | 'lg' | 'xl';
  justify?: 'start' | 'center' | 'end' | 'between' | 'around' | 'evenly';
  align?: 'start' | 'center' | 'end' | 'stretch' | 'baseline';
  wrap?: boolean;
}

export interface GridProps extends BaseComponentProps {
  cols?: number;
  gap?: 'xs' | 'sm' | 'md' | 'lg' | 'xl';
  rows?: number;
}

export interface SectionProps extends BaseComponentProps {
  backgroundColor?: string;
  padding?: 'none' | 'sm' | 'md' | 'lg' | 'xl';
}

// ============================================================================
// Navigation Components
// ============================================================================

export interface NavItemProps {
  label: string;
  href?: string;
  active?: boolean;
  icon?: string;
  disabled?: boolean;
  onClick?: (event: MouseEvent) => void;
}

export interface NavbarProps extends BaseComponentProps {
  items?: NavItemProps[];
  logo?: string;
  logoText?: string;
  brand?: string;
  rightContent?: HTMLElement;
  sticky?: boolean;
}

export interface SidebarProps extends BaseComponentProps {
  items?: NavItemProps[];
  collapsible?: boolean;
  defaultCollapsed?: boolean;
}

export interface TabItem {
  label: string;
  id: string;
  active?: boolean;
  disabled?: boolean;
  onClick?: (event: MouseEvent) => void;
}

export interface TabsProps extends BaseComponentProps {
  tabs: TabItem[];
}

export interface BreadcrumbItem {
  label: string;
  href?: string;
}

export interface BreadcrumbsProps extends BaseComponentProps {
  items: BreadcrumbItem[];
  separator?: string;
}

// ============================================================================
// Tag Input Component
// ============================================================================

export interface TagInputProps extends BaseComponentProps {
  tags?: string[];
  placeholder?: string;
  maxTags?: number;
  disabled?: boolean;
  autocompleteOptions?: string[];
  onTagsChange?: (tags: string[]) => void;
}
