String? requiredText(String? value, {String field = 'This field'}) {
  if (value == null || value.trim().isEmpty) return '$field is required.';
  return null;
}

String? emailValidator(String? value) {
  if (value == null || !RegExp(r'^[^@\s]+@[^@\s]+\.[^@\s]+$').hasMatch(value)) {
    return 'Enter a valid email address.';
  }
  return null;
}

String? passwordValidator(String? value) {
  if (value == null || value.length < 8) return 'Use at least 8 characters.';
  return null;
}
