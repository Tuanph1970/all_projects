// Utility function to filter out custom props from being passed to DOM elements
// This prevents styled-components warnings about unknown props

const shouldForwardProp = (prop) => {
  // List of custom props that should NOT be forwarded to DOM elements
  const customProps = [
    'grow',
    'center',
    'spacing',
    'variant',
    'active',
    'disabled',
    'size',
  ];

  // Return false if prop is in the custom props list (don't forward to DOM)
  // Return true otherwise (forward to DOM)
  return !customProps.includes(prop);
};

export default shouldForwardProp;
