// jest-dom adds custom jest matchers for asserting on DOM nodes.
// allows you to do things like:
// expect(element).toHaveTextContent(/react/i)
// learn more: https://github.com/testing-library/jest-dom
import '@testing-library/jest-dom';

// jsdom does not implement ResizeObserver, and recharts' ResponsiveContainer
// requires it — without this, mounting ANY page that draws a recharts chart
// throws "ReferenceError: ResizeObserver is not defined" from inside an effect,
// React unmounts the tree, and the test then fails with an empty <body>. The
// error names recharts nowhere, so it reads like the component is broken.
//
// A minimal stub is enough: these tests assert on the narrative text and the
// form, not on chart geometry, and jsdom reports zero dimensions anyway.
if (typeof global.ResizeObserver === 'undefined') {
  global.ResizeObserver = class {
    observe() {}

    unobserve() {}

    disconnect() {}
  };
}
