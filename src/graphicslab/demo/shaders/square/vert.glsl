#version 330

out float value;
out float square;

void main() {
  value = gl_VertexID;
  square = pow(gl_VertexID, 2);
}
